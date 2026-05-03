from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

from pydantic import BaseModel

from if_then_mvp.simulation import BranchAssessmentPayload, FirstReplyPayload, TurnStatePayload


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_realism_provider_regression.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_realism_provider_regression", RUNNER_PATH)
assert RUNNER_SPEC is not None
assert RUNNER_SPEC.loader is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)


class FakeProviderLLM:
    def __init__(self, responses: list[BaseModel]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        response = self._responses[len(self.calls) - 1]
        assert isinstance(response, response_model)
        return response


class FakeResponsesTransport:
    def __init__(self, output_texts: list[str]) -> None:
        self._output_texts = output_texts
        self.requests: list[dict] = []

    def post_responses(self, *, base_url: str, api_key: str, payload: dict):
        self.requests.append(
            {
                "base_url": base_url,
                "api_key": api_key,
                "payload": payload,
            }
        )
        return {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": self._output_texts[len(self.requests) - 1],
                        }
                    ],
                }
            ],
        }


def _state_payload() -> TurnStatePayload:
    return TurnStatePayload(
        relationship_temperature="mixed",
        tension_level="medium",
        openness_level="limited",
        initiative_balance="self_leading",
        defensiveness_level="medium",
        relationship_phase="sensitive_boundary",
        active_sensitive_topics=[],
        state_rationale="即时状态仍需保守。",
    )


def _assessment(*, branch_direction: str = "limited_positive") -> BranchAssessmentPayload:
    return BranchAssessmentPayload(
        branch_direction=branch_direction,
        state_shift_summary="改写降低了压力，但只能有限缓和。",
        other_immediate_feeling="压力下降但仍保留",
        reply_strategy="guarded_acknowledgement",
        risk_flags=["核心边界仍敏感"],
        modeler_only_risk_sources=["future evidence suggests conservative handling"],
        leakage_boundary_notes="future evidence is modeler-only.",
        confidence=0.62,
    )


def _first_reply(text: str) -> FirstReplyPayload:
    return FirstReplyPayload(
        first_reply_text=text,
        strategy_used="guarded_acknowledgement",
        first_reply_style_notes="短句、保留。",
        state_after_turn=_state_payload(),
    )


def test_evaluate_case_output_detects_future_leakage():
    case = runner.select_cases(runner.load_baseline(), case_ids=["c01-rp2-stop-running"])[0]

    result = runner.evaluate_case_output(
        case=case,
        assessment=_assessment(),
        first_reply=_first_reply("其实我就是因为以前那段关系才会怕确定。"),
    )

    assert result["status"] == "completed"
    assert result["leakage"]["passed"] is False
    assert result["leakage"]["hits"] == [{"term": "以前那段关系"}]
    assert "Blocker" in result["manual_review"]["notes"][-1]


def test_live_regression_uses_production_prompt_builders_with_fake_provider():
    case = runner.select_cases(runner.load_baseline(), case_ids=["c01-rp1-possession-joke"])[0]
    fake_llm = FakeProviderLLM(
        [
            _assessment(),
            _first_reply("嗯，先这样听着也可以。"),
        ]
    )

    report = runner.run_live_regression(
        baseline_path=Path("tests/fixtures/realism_baseline/cases.json"),
        cases=[case],
        llm_client=fake_llm,
        provider={"status": "configured", "source": "fake", "role": "api", "model": "fake-model"},
    )

    assert report["status"] == "completed"
    assert report["summary"]["completed_case_count"] == 1
    assert report["summary"]["leakage_case_count"] == 0
    assert fake_llm.calls[0]["response_model"] is BranchAssessmentPayload
    assert fake_llm.calls[1]["response_model"] is FirstReplyPayload
    assert "modeler-only future evidence JSONL:" in fake_llm.calls[0]["user_prompt"]
    assert "future evidence" in fake_llm.calls[1]["user_prompt"]


def test_load_env_file_supports_project_llm_config_keys(tmp_path):
    env_file = tmp_path / "llm_config.env"
    env_file.write_text(
        "\n".join(
            [
                "API_BASE_URL=https://provider.example/v1",
                "API_KEY=secret-test-key",
                "MODEL_NAME=gpt-test",
            ]
        ),
        encoding="utf-8",
    )

    config = runner.load_env_file(env_file)

    assert config.base_url == "https://provider.example/v1"
    assert config.api_key == "secret-test-key"
    assert config.model == "gpt-test"


def test_responses_client_posts_json_object_request_and_validates_model():
    assessment = _assessment().model_dump_json()
    transport = FakeResponsesTransport([assessment])
    client = runner.ResponsesJSONClient(
        base_url="https://provider.example/v1",
        api_key="secret-test-key",
        model="gpt-test",
        transport=transport,
    )

    payload = client.chat_json(
        system_prompt="system",
        user_prompt="user",
        response_model=BranchAssessmentPayload,
    )

    assert payload.branch_direction == "limited_positive"
    assert transport.requests[0]["base_url"] == "https://provider.example/v1"
    assert transport.requests[0]["api_key"] == "secret-test-key"
    assert transport.requests[0]["payload"]["model"] == "gpt-test"
    assert transport.requests[0]["payload"]["instructions"] == "system"
    assert transport.requests[0]["payload"]["input"] == "user"
    assert transport.requests[0]["payload"]["text"] == {"format": {"type": "json_object"}}


def test_responses_client_repairs_invalid_structured_output():
    invalid_reply = json.dumps(
        {
            "first_reply_text": "嗯，先这样听着也可以。",
            "strategy_used": "guarded_acknowledgement",
            "first_reply_style_notes": "短句、保留。",
            "state_after_turn": {
                "relationship_temperature": "mixed",
                "tension_level": "medium",
                "openness_level": "limited",
                "initiative_balance": "self_leading",
                "defensiveness_level": "medium",
                "relationship_phase": "sensitive_boundary",
                "active_sensitive_topics": [],
            },
        },
        ensure_ascii=False,
    )
    repaired_reply = _first_reply("嗯，先这样听着也可以。").model_dump_json()
    transport = FakeResponsesTransport([invalid_reply, repaired_reply])
    client = runner.ResponsesJSONClient(
        base_url="https://provider.example/v1",
        api_key="secret-test-key",
        model="gpt-test",
        transport=transport,
    )

    payload = client.chat_json(
        system_prompt="system",
        user_prompt="user",
        response_model=FirstReplyPayload,
    )

    assert payload.state_after_turn.state_rationale == "即时状态仍需保守。"
    assert len(transport.requests) == 2
    assert "目标 JSON Schema" in transport.requests[1]["payload"]["input"]


def test_env_file_provider_report_does_not_include_api_key(tmp_path):
    case = runner.select_cases(runner.load_baseline(), case_ids=["c01-rp1-possession-joke"])[0]
    env_file = tmp_path / "llm_config.env"
    output_json = tmp_path / "report.json"
    env_file.write_text(
        "\n".join(
            [
                "API_BASE_URL=https://provider.example/v1",
                "API_KEY=secret-test-key",
                "MODEL_NAME=gpt-test",
            ]
        ),
        encoding="utf-8",
    )
    transport = FakeResponsesTransport(
        [
            _assessment().model_dump_json(),
            _first_reply("嗯，先这样听着也可以。").model_dump_json(),
        ]
    )
    client = runner.ResponsesJSONClient(
        base_url="https://provider.example/v1",
        api_key="secret-test-key",
        model="gpt-test",
        transport=transport,
    )

    report = runner.run_live_regression(
        baseline_path=Path("tests/fixtures/realism_baseline/cases.json"),
        cases=[case],
        llm_client=client,
        provider={"status": "configured", "source": env_file.name, "role": "api", "model": "gpt-test"},
    )
    runner.write_report_files(report=report, output_json=output_json, output_markdown=None)

    report_text = output_json.read_text(encoding="utf-8")
    assert "secret-test-key" not in report_text
    assert "llm_config.env" in report_text
    assert "tests\\fixtures\\realism_synthetic" in report["dataset_path"] or "tests/fixtures/realism_synthetic" in report["dataset_path"]


def test_skipped_report_marks_every_case_without_failing():
    cases = runner.select_cases(runner.load_baseline(), max_cases=2)

    report = runner.build_skipped_report(
        baseline_path=Path("tests/fixtures/realism_baseline/cases.json"),
        cases=cases,
        skip_reason="Missing llm_config.env.",
    )

    assert report["status"] == "skipped"
    assert report["summary"]["skipped_case_count"] == 2
    assert {case["status"] for case in report["cases"]} == {"skipped"}


def test_replay_cli_writes_json_and_markdown_reports(tmp_path):
    replay_path = tmp_path / "replay.json"
    output_json = tmp_path / "report.json"
    output_markdown = tmp_path / "report.md"
    replay_path.write_text(
        json.dumps(
            {
                "cases": {
                    "c01-rp1-possession-joke": {
                        "assessment": {
                            "branch_direction": "limited_positive",
                            "risk_flags": ["仍需保守"],
                            "modeler_only_risk_sources": ["future evidence boundary"],
                        },
                        "first_reply_text": "嗯，先慢慢聊。",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = runner.main(
        [
            "--case-id",
            "c01-rp1-possession-joke",
            "--replay-output",
            str(replay_path),
            "--output-json",
            str(output_json),
            "--output-markdown",
            str(output_markdown),
        ]
    )

    assert exit_code == 0
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["provider"]["status"] == "replay"
    assert report["summary"]["completed_case_count"] == 1
    assert "# Realism Provider Regression Report" in output_markdown.read_text(encoding="utf-8")
