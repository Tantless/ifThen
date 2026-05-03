from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from if_then_mvp.llm import ChatJSONClient
from if_then_mvp.runtime_llm import build_runtime_llm_client
from if_then_mvp.simulation import assess_branch, generate_first_reply


BASELINE_PATH = REPO_ROOT / "tests" / "fixtures" / "realism_baseline" / "cases.json"
REALISM_SYNTHETIC_ROOT = REPO_ROOT / "tests" / "fixtures" / "realism_synthetic"
DEFAULT_ENV_FILE = REPO_ROOT / "llm_config.env"
RUNNER_NAME = "realism-provider-regression"
SCHEMA_VERSION = 1
PROVIDER_ROLE = "api"
TModel = TypeVar("TModel", bound=BaseModel)


class ProviderConfigError(RuntimeError):
    pass


class ResponsesProviderError(RuntimeError):
    pass


class ResponsesTransport(Protocol):
    def post_responses(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class EnvLLMConfig:
    base_url: str
    api_key: str
    model: str


@dataclass(slots=True)
class OpenAIResponsesTransport:
    timeout_seconds: float = 120.0

    def post_responses(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{base_url.rstrip('/')}/responses", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ResponsesProviderError(f"Responses request failed: {type(exc).__name__}") from exc
        except ValueError as exc:
            raise ResponsesProviderError("Responses request returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise ResponsesProviderError("Responses response body must be a JSON object")
        return data


@dataclass(slots=True)
class ResponsesJSONClient:
    base_url: str
    api_key: str
    model: str
    transport: ResponsesTransport = field(default_factory=OpenAIResponsesTransport)
    max_output_tokens: int = 2048

    def chat_json(self, *, system_prompt: str, user_prompt: str, response_model: type[TModel]) -> TModel:
        content = self._post_json_prompt(system_prompt=system_prompt, user_prompt=user_prompt)
        try:
            return response_model.model_validate_json(content)
        except ValidationError:
            repaired_content = self._repair_structured_output(
                invalid_content=content,
                response_model=response_model,
            )
            try:
                return response_model.model_validate_json(repaired_content)
            except ValidationError as exc:
                raise ResponsesProviderError("Failed to validate structured Responses output") from exc

    def _post_json_prompt(self, *, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": self.max_output_tokens,
        }
        response_payload = self.transport.post_responses(
            base_url=self.base_url,
            api_key=self.api_key,
            payload=payload,
        )
        return _extract_responses_output_text(response_payload)

    def _repair_structured_output(self, *, invalid_content: str, response_model: type[BaseModel]) -> str:
        schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=False, sort_keys=True)
        repair_prompt = (
            "目标 JSON Schema：\n"
            f"{schema_json}\n\n"
            "当前 JSON 内容：\n"
            f"{invalid_content}\n\n"
            "请只返回一个符合 schema 的 JSON 对象。"
            "尽量保留原意，并用最保守、最安全的值补齐缺失字段。"
        )
        return self._post_json_prompt(
            system_prompt="请将给定的 JSON 修复为符合要求的结构。",
            user_prompt=repair_prompt,
        )


def load_env_file(path: Path = DEFAULT_ENV_FILE) -> EnvLLMConfig:
    if not path.exists():
        raise ProviderConfigError(f"Missing env file: {path.name}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    base_url = values.get("API_BASE_URL") or values.get("API_URL")
    api_key = values.get("API_KEY")
    model = values.get("MODEL_NAME")
    missing = [
        key
        for key, value in (
            ("API_BASE_URL", base_url),
            ("API_KEY", api_key),
            ("MODEL_NAME", model),
        )
        if not value
    ]
    if missing:
        raise ProviderConfigError(f"env file missing required keys: {', '.join(missing)}")
    return EnvLLMConfig(base_url=str(base_url), api_key=str(api_key), model=str(model))


def build_provider_client(
    *,
    env_file: Path = DEFAULT_ENV_FILE,
) -> tuple[ChatJSONClient, dict[str, Any]]:
    try:
        config = load_env_file(env_file)
    except ProviderConfigError as env_error:
        try:
            runtime_client = build_runtime_llm_client(role=PROVIDER_ROLE)
        except RuntimeError as runtime_error:
            raise ProviderConfigError(f"{env_error}; runtime fallback unavailable: {runtime_error}") from runtime_error
        return runtime_client, {
            "status": "configured",
            "source": "runtime_config",
            "role": PROVIDER_ROLE,
            "model": getattr(runtime_client, "chat_model", "unknown"),
        }

    return ResponsesJSONClient(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    ), {
        "status": "configured",
        "source": env_file.name,
        "api": "responses",
        "role": PROVIDER_ROLE,
        "model": config.model,
    }


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_cases(
    payload: dict[str, Any],
    *,
    case_ids: list[str] | None = None,
    max_cases: int | None = None,
) -> list[dict[str, Any]]:
    cases = list(payload["cases"])
    if case_ids:
        requested = set(case_ids)
        cases = [case for case in cases if case["id"] in requested]
        found = {case["id"] for case in cases}
        missing = sorted(requested - found)
        if missing:
            raise ValueError(f"Unknown baseline case id(s): {', '.join(missing)}")
    if max_cases is not None:
        cases = cases[:max_cases]
    return cases


def build_case_context_pack(case: dict[str, Any]) -> dict[str, Any]:
    target = case["target"]
    evidence = case["modeler_only_evidence"]
    return {
        "schema_version": "provider-regression-baseline-v1",
        "baseline_case_id": case["id"],
        "source_fixture": case["source_fixture"],
        "scenario": case["scenario"],
        "original_message_text": target["original_text"],
        "replacement_content": case["rewrite_text"],
        "target_message": {
            "sequence_no": target["sequence_no"],
            "speaker_role": target["speaker_role"],
            "cutoff_timestamp": target["cutoff_timestamp"],
        },
        "moment_state_estimate": _risk_to_moment_state(case["expected_risk"]),
        "persona_self": _baseline_persona(role="self"),
        "persona_other": _baseline_persona(role="other"),
        "current_segment_history": [
            {
                "speaker_role": "self",
                "content_text": target["original_text"],
                "timestamp": target["cutoff_timestamp"],
            },
            {
                "speaker_role": "self",
                "content_text": case["rewrite_text"],
                "timestamp": target["cutoff_timestamp"],
                "branch_only": True,
            },
        ],
        "cutoff_safe_facts": {
            "source": "baseline_fixture",
            "note": "Only target message, rewrite text, scenario label, and committed fixture metadata are character-known.",
        },
        "related_topic_digests": [
            {
                "topic_name": case["scenario"],
                "summary": "Baseline case context; use only as cutoff-safe scenario framing, not as future knowledge.",
                "source": "baseline_fixture",
            }
        ],
        "future_evidence_digests": [
            {
                "source": "baseline_fixture",
                "reveal_timestamp": evidence["reveal_timestamp"],
                "summary": evidence["truth_digest"],
                "evidence_anchor": evidence["evidence_anchor"],
                "forbidden_character_knowledge": evidence["forbidden_character_knowledge"],
                "policy": "modeler_only_not_character_known",
            }
        ],
        "branch_facts": {"generated_branch_messages": []},
        "evidence_policy": {
            "cutoff_safe_facts": "character_known",
            "future_evidence_digests": "modeler_only_not_character_known",
            "branch_facts": "branch_only_generated_facts",
        },
        "retrieval_trace": {
            "source": "provider_regression_fixture",
            "future_evidence_count": 1,
        },
        "retrieval_budget": {
            "future_evidence_digests": {
                "limit": 1,
                "candidate_count": 1,
                "selected_count": 1,
                "overflow_count": 0,
            }
        },
        "retrieval_warnings": [],
    }


def run_live_regression(
    *,
    baseline_path: Path,
    cases: list[dict[str, Any]],
    llm_client: ChatJSONClient,
    provider: dict[str, Any],
) -> dict[str, Any]:
    results = []
    for case in cases:
        try:
            context_pack = build_case_context_pack(case)
            assessment = assess_branch(llm_client=llm_client, context_pack=context_pack)
            first_reply = generate_first_reply(
                llm_client=llm_client,
                context_pack=context_pack,
                assessment=assessment,
            )
            results.append(evaluate_case_output(case=case, assessment=assessment, first_reply=first_reply))
        except Exception as exc:  # pragma: no cover - exercised by live provider failures.
            results.append(
                {
                    "case_id": case["id"],
                    "scenario": case["scenario"],
                    "status": "error",
                    "error": str(exc),
                    "expected_risk": case["expected_risk"],
                }
            )
    return build_report(
        baseline_path=baseline_path,
        provider=provider,
        case_results=results,
    )


def run_replay_regression(
    *,
    baseline_path: Path,
    cases: list[dict[str, Any]],
    replay_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    results = []
    for case in cases:
        replay = replay_outputs.get(case["id"])
        if replay is None:
            results.append(
                {
                    "case_id": case["id"],
                    "scenario": case["scenario"],
                    "status": "error",
                    "error": "Replay output missing for case.",
                    "expected_risk": case["expected_risk"],
                }
            )
            continue
        results.append(
            evaluate_case_output(
                case=case,
                assessment=replay.get("assessment") or {},
                first_reply=replay.get("first_reply") or {"first_reply_text": replay.get("first_reply_text", "")},
            )
        )
    return build_report(
        baseline_path=baseline_path,
        provider={"status": "replay", "role": None, "model": None},
        case_results=results,
    )


def build_skipped_report(
    *,
    baseline_path: Path,
    cases: list[dict[str, Any]],
    skip_reason: str,
) -> dict[str, Any]:
    case_results = [
        {
            "case_id": case["id"],
            "scenario": case["scenario"],
            "status": "skipped",
            "skip_reason": skip_reason,
            "expected_risk": case["expected_risk"],
        }
        for case in cases
    ]
    return build_report(
        baseline_path=baseline_path,
        provider={"status": "missing", "source": None, "role": PROVIDER_ROLE, "model": None},
        case_results=case_results,
        skip_reason=skip_reason,
    )


def evaluate_case_output(
    *,
    case: dict[str, Any],
    assessment: Any,
    first_reply: Any,
) -> dict[str, Any]:
    assessment_payload = _model_dump(assessment)
    first_reply_payload = _model_dump(first_reply)
    first_reply_text = str(first_reply_payload.get("first_reply_text", ""))
    forbidden_terms = case["modeler_only_evidence"]["forbidden_character_knowledge"]
    leakage_hits = find_forbidden_terms(first_reply_text, forbidden_terms)
    risk_alignment = evaluate_risk_alignment(case=case, assessment=assessment_payload)

    manual_notes = [
        "Review whether the reply is over-optimistic, over-mature, or over-therapeutic.",
        "Compare reply length and rhythm against historical persona/style evidence before accepting.",
    ]
    if risk_alignment["notes"]:
        manual_notes.extend(risk_alignment["notes"])
    if leakage_hits:
        manual_notes.append("Blocker: generated dialogue contains modeler-only future evidence.")

    return {
        "case_id": case["id"],
        "scenario": case["scenario"],
        "status": "completed",
        "expected_risk": case["expected_risk"],
        "target": case["target"],
        "rewrite_text": case["rewrite_text"],
        "leakage": {
            "passed": not leakage_hits,
            "forbidden_terms": forbidden_terms,
            "hits": leakage_hits,
        },
        "risk_alignment": risk_alignment,
        "manual_review": {
            "required": True,
            "notes": manual_notes,
        },
        "provider_output": {
            "assessment": assessment_payload,
            "first_reply": first_reply_payload,
        },
    }


def find_forbidden_terms(text: str, forbidden_terms: list[str]) -> list[dict[str, str]]:
    lowered_text = text.casefold()
    hits = []
    for term in forbidden_terms:
        normalized = str(term).strip()
        if not normalized:
            continue
        if normalized in text or normalized.casefold() in lowered_text:
            hits.append({"term": normalized})
    return hits


def evaluate_risk_alignment(*, case: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    expected_risk = case["expected_risk"]
    branch_direction = str(assessment.get("branch_direction", ""))
    direction_key = branch_direction.casefold()
    risk_flags = _string_list(assessment.get("risk_flags"))
    risk_sources = _string_list(assessment.get("modeler_only_risk_sources"))
    notes = []

    if expected_risk == "high":
        if not risk_flags and not risk_sources:
            notes.append("Expected high risk, but assessment has no risk flags or modeler-only risk sources.")
        if _looks_strongly_closer(direction_key):
            notes.append("Expected high risk, but branch_direction appears strongly optimistic.")
    elif expected_risk == "medium":
        if _looks_strongly_closer(direction_key) and not risk_flags:
            notes.append("Expected medium risk, but branch_direction appears optimistic without risk flags.")

    status = "needs_manual_review" if notes else "aligned_or_sampling_required"
    return {
        "status": status,
        "expected_risk": expected_risk,
        "branch_direction": branch_direction,
        "risk_flags": risk_flags,
        "modeler_only_risk_sources": risk_sources,
        "notes": notes,
    }


def build_report(
    *,
    baseline_path: Path,
    provider: dict[str, Any],
    case_results: list[dict[str, Any]],
    skip_reason: str | None = None,
) -> dict[str, Any]:
    summary = summarize_results(case_results)
    if summary["error_case_count"]:
        status = "completed_with_errors"
    elif summary["leakage_case_count"]:
        status = "completed_with_failures"
    elif summary["skipped_case_count"] == summary["case_count"]:
        status = "skipped"
    else:
        status = "completed"

    return {
        "schema_version": SCHEMA_VERSION,
        "runner": RUNNER_NAME,
        "status": status,
        "generated_at_ms": int(time.time() * 1000),
        "baseline_path": str(baseline_path),
        "dataset_path": str(REALISM_SYNTHETIC_ROOT),
        "provider": provider,
        "skip_reason": skip_reason,
        "summary": summary,
        "cases": case_results,
    }


def summarize_results(case_results: list[dict[str, Any]]) -> dict[str, int]:
    completed = [case for case in case_results if case["status"] == "completed"]
    skipped = [case for case in case_results if case["status"] == "skipped"]
    errors = [case for case in case_results if case["status"] == "error"]
    leakage = [case for case in completed if not case["leakage"]["passed"]]
    risk_review = [
        case
        for case in completed
        if case["risk_alignment"]["status"] == "needs_manual_review"
    ]
    return {
        "case_count": len(case_results),
        "completed_case_count": len(completed),
        "skipped_case_count": len(skipped),
        "error_case_count": len(errors),
        "leakage_case_count": len(leakage),
        "risk_review_case_count": len(risk_review),
        "manual_review_required_case_count": len(completed),
    }


def build_markdown_report(report: dict[str, Any]) -> str:
    provider = report["provider"]
    summary = report["summary"]
    lines = [
        "# Realism Provider Regression Report",
        "",
        f"Status: {report['status']}",
        f"Generated at ms: {report['generated_at_ms']}",
        f"Baseline: {report['baseline_path']}",
        f"Dataset: {report['dataset_path']}",
        f"Provider: {provider.get('status')} / {provider.get('source')} / {provider.get('role')} / {provider.get('model')}",
    ]
    if report.get("skip_reason"):
        lines.append(f"Skip reason: {report['skip_reason']}")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Cases: {summary['case_count']}",
            f"- Completed: {summary['completed_case_count']}",
            f"- Skipped: {summary['skipped_case_count']}",
            f"- Errors: {summary['error_case_count']}",
            f"- Leakage failures: {summary['leakage_case_count']}",
            f"- Risk review flags: {summary['risk_review_case_count']}",
            "",
            "## Cases",
            "",
            "| case | status | risk | leakage | risk review | first reply |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in report["cases"]:
        first_reply = ""
        if case["status"] == "completed":
            first_reply = str((case["provider_output"]["first_reply"]).get("first_reply_text", ""))
        leakage_status = "-"
        risk_status = "-"
        if case["status"] == "completed":
            leakage_status = "pass" if case["leakage"]["passed"] else "fail"
            risk_status = case["risk_alignment"]["status"]
        lines.append(
            "| {case_id} | {status} | {risk} | {leakage} | {risk_status} | {reply} |".format(
                case_id=_escape_md_cell(case["case_id"]),
                status=_escape_md_cell(case["status"]),
                risk=_escape_md_cell(case["expected_risk"]),
                leakage=_escape_md_cell(leakage_status),
                risk_status=_escape_md_cell(risk_status),
                reply=_escape_md_cell(_truncate(first_reply, 80)),
            )
        )
    return "\n".join(lines)


def load_replay_outputs(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_cases = payload.get("cases", payload)
    if isinstance(raw_cases, dict):
        return {str(case_id): value for case_id, value in raw_cases.items()}
    if isinstance(raw_cases, list):
        return {str(item["case_id"]): item for item in raw_cases}
    raise ValueError("Replay output must be a case-id mapping or a list of case records.")


def write_report_files(
    *,
    report: dict[str, Any],
    output_json: Path | None,
    output_markdown: Path | None,
) -> None:
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if output_markdown is not None:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(build_markdown_report(report), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fixed realism baseline cases against a live or replayed provider.")
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-markdown", type=Path, default=None)
    parser.add_argument("--replay-output", type=Path, default=None)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument(
        "--require-provider",
        action="store_true",
        help="Return a non-zero exit code when provider configuration is missing instead of writing a skipped report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    baseline = load_baseline(args.baseline)
    cases = select_cases(baseline, case_ids=args.case_id, max_cases=args.max_cases)

    if args.replay_output is not None:
        report = run_replay_regression(
            baseline_path=args.baseline,
            cases=cases,
            replay_outputs=load_replay_outputs(args.replay_output),
        )
    else:
        try:
            llm_client, provider = build_provider_client(env_file=args.env_file)
        except ProviderConfigError as exc:
            if args.require_provider:
                print(str(exc), file=sys.stderr)
                return 2
            report = build_skipped_report(
                baseline_path=args.baseline,
                cases=cases,
                skip_reason=str(exc),
            )
        else:
            report = run_live_regression(
                baseline_path=args.baseline,
                cases=cases,
                llm_client=llm_client,
                provider=provider,
            )

    write_report_files(
        report=report,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
    )
    if args.output_json is None and args.output_markdown is None:
        print(build_markdown_report(report))

    if report["status"] in {"completed_with_errors", "completed_with_failures"}:
        return 1
    return 0


def _model_dump(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if isinstance(payload, dict):
        return dict(payload)
    raise TypeError(f"Unsupported payload type: {type(payload).__name__}")


def _extract_responses_output_text(response_payload: dict[str, Any]) -> str:
    status = response_payload.get("status")
    if status not in {None, "completed"}:
        raise ResponsesProviderError(f"Responses request did not complete: {status}")
    for item in response_payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content_item in item.get("content") or []:
            if (
                isinstance(content_item, dict)
                and content_item.get("type") == "output_text"
                and isinstance(content_item.get("text"), str)
            ):
                return content_item["text"]
    raise ResponsesProviderError("Responses output did not contain output_text")


def _risk_to_moment_state(expected_risk: str) -> dict[str, Any]:
    if expected_risk == "high":
        return {
            "relationship_temperature": "mixed",
            "tension_level": "high",
            "openness_level": "limited",
            "initiative_balance": "self_leading",
            "defensiveness_level": "medium_high",
            "relationship_phase": "sensitive_boundary",
            "active_sensitive_topics": ["future-evidence-risk"],
            "state_rationale": "Baseline fixture expects high risk; provider output should remain conservative.",
        }
    if expected_risk == "medium":
        return {
            "relationship_temperature": "warm_but_uncertain",
            "tension_level": "medium",
            "openness_level": "medium",
            "initiative_balance": "self_leading",
            "defensiveness_level": "medium",
            "relationship_phase": "limited_repair_or_window",
            "active_sensitive_topics": ["bounded-improvement"],
            "state_rationale": "Baseline fixture expects medium risk; provider output should avoid dramatic improvement.",
        }
    return {
        "relationship_temperature": "stable",
        "tension_level": "low",
        "openness_level": "medium",
        "initiative_balance": "balanced",
        "defensiveness_level": "low",
        "relationship_phase": "stable",
        "active_sensitive_topics": [],
        "state_rationale": "Baseline fixture expects low risk.",
    }


def _baseline_persona(*, role: str) -> dict[str, Any]:
    if role == "other":
        return {
            "role": "other",
            "summary": "Synthetic baseline persona. Reply naturally, briefly, and avoid sudden therapeutic self-analysis.",
            "deterministic_style_profile": {
                "reply_envelope": {
                    "preferred_bubble_count": 1,
                    "max_bubble_count": 2,
                    "max_chars_per_bubble": 48,
                    "pressure_boundary": "Keep replies bounded under tension.",
                },
                "generation_hints": [
                    "Prefer short, immediate chat phrasing.",
                    "Do not become more mature, more articulate, or more intimate than the current state supports.",
                ],
            },
        }
    return {
        "role": "self",
        "summary": "Synthetic baseline self persona. The user rewrite is the source of truth.",
        "deterministic_style_profile": {
            "reply_envelope": {
                "preferred_bubble_count": 1,
                "max_bubble_count": 2,
                "max_chars_per_bubble": 64,
            },
            "generation_hints": ["Do not rewrite or continue self in the first-reply regression."],
        },
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _looks_strongly_closer(direction_key: str) -> bool:
    optimistic_markers = ("closer", "warming", "mutual", "repairing", "明显", "升温", "成功")
    limiting_markers = ("slight", "limited", "guard", "neutral", "risk", "conservative", "有限", "保守")
    return any(marker in direction_key for marker in optimistic_markers) and not any(
        marker in direction_key for marker in limiting_markers
    )


def _escape_md_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
