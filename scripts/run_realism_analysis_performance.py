from __future__ import annotations

import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sqlalchemy import select

from if_then_mvp.db import init_db, session_scope
from if_then_mvp.llm import ChatJSONClient
from if_then_mvp.models import (
    AnalysisJob,
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    Topic,
    TopicLink,
)
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.responses_json_client import (
    DEFAULT_ENV_FILE,
    OpenAIResponsesTransport,
    ProviderConfigError,
    ResponsesJSONClient,
    load_env_file,
)
from if_then_mvp.runtime_llm import build_runtime_llm_client
from if_then_mvp.worker import ConsoleProgressReporter, run_next_job


DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "realism_synthetic"
DEFAULT_RUNS_ROOT = REPO_ROOT / ".data" / "perf-runs"
RUNNER_NAME = "realism-analysis-performance"
SCHEMA_VERSION = 1
PROVIDER_ROLE = "worker"


@dataclass(frozen=True, slots=True)
class FixtureCase:
    case_id: str
    conversation_path: Path


def build_worker_client(
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
            "api": "chat_completions",
        }

    return ResponsesJSONClient(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        transport=OpenAIResponsesTransport(
            timeout_seconds=300.0,
            max_attempts=4,
            retry_backoff_seconds=8.0,
        ),
        max_output_tokens=1024,
    ), {
        "status": "configured",
        "source": env_file.name,
        "api": "responses",
        "model": config.model,
        "role": PROVIDER_ROLE,
    }


def discover_fixture_cases(
    fixture_root: Path,
    *,
    case_ids: list[str] | None = None,
    max_cases: int | None = None,
) -> list[FixtureCase]:
    cases = [
        FixtureCase(case_id=path.name, conversation_path=path / "conversation.txt")
        for path in sorted(fixture_root.iterdir())
        if path.is_dir() and (path / "conversation.txt").exists()
    ]
    if case_ids:
        requested = set(case_ids)
        cases = [case for case in cases if case.case_id in requested]
        found = {case.case_id for case in cases}
        missing = sorted(requested - found)
        if missing:
            raise ValueError(f"Unknown fixture case id(s): {', '.join(missing)}")
    if max_cases is not None:
        cases = cases[:max_cases]
    return cases


def run_fixture_analyses(
    *,
    fixture_cases: list[FixtureCase],
    llm_client: ChatJSONClient,
    provider: dict[str, Any],
    run_root: Path,
    self_display_name: str,
) -> dict[str, Any]:
    case_results = [
        run_case_analysis(
            case=case,
            llm_client=llm_client,
            run_root=run_root,
            self_display_name=self_display_name,
            provider=provider,
        )
        for case in fixture_cases
    ]
    return build_report(
        fixture_root=fixture_cases[0].conversation_path.parents[1] if fixture_cases else DEFAULT_FIXTURE_ROOT,
        run_root=run_root,
        provider=provider,
        case_results=case_results,
    )


def run_case_analysis(
    *,
    case: FixtureCase,
    llm_client: ChatJSONClient,
    run_root: Path,
    self_display_name: str,
    provider: dict[str, Any],
) -> dict[str, Any]:
    case_root = run_root / case.case_id
    data_dir = case_root / "app-data"
    worker_log_path = case_root / "worker.log"
    case_root.mkdir(parents=True, exist_ok=True)
    logs: list[str] = []

    with _temporary_environment({"IF_THEN_DATA_DIR": str(data_dir)}):
        init_db()
        conversation_id, job_id = seed_analysis_job(
            conversation_path=case.conversation_path,
            self_display_name=self_display_name,
        )
        reporter = ConsoleProgressReporter(printer=logs.append, time_fn=time.monotonic)
        started_at = time.monotonic()
        processed = run_next_job(llm_client=llm_client, progress_reporter=reporter)
        wall_clock_seconds = round(max(0.0, time.monotonic() - started_at), 3)

        with session_scope() as session:
            job = session.get(AnalysisJob, job_id)
            conversation = session.get(Conversation, conversation_id)
            if job is None or conversation is None:
                raise RuntimeError(f"Analysis artifacts missing for case {case.case_id}")
            artifact_counts, quality_checks = collect_analysis_artifacts(
                session,
                conversation_id=conversation_id,
                include_quality_checks=job.status == "completed",
            )
            performance = dict(job.payload_json.get("performance") or {})

    worker_log_path.write_text("\n".join(logs), encoding="utf-8")
    db_path = data_dir / "db" / "if_then_mvp.sqlite3"
    message_count = int((performance.get("input_counts") or {}).get("messages", artifact_counts["messages"]))
    segment_count = int((performance.get("input_counts") or {}).get("segments", artifact_counts["segments"]))

    return {
        "case_id": case.case_id,
        "status": "completed" if processed and job.status == "completed" else "error",
        "conversation_path": _relative_path(case.conversation_path),
        "data_dir": _relative_path(data_dir),
        "worker_log_path": _relative_path(worker_log_path),
        "db_path": _relative_path(db_path),
        "provider": {
            "source": provider.get("source"),
            "role": provider.get("role"),
            "model": provider.get("model"),
            "api": provider.get("api"),
        },
        "message_count": message_count,
        "segment_count": segment_count,
        "wall_clock_seconds": wall_clock_seconds,
        "job_status": job.status,
        "error_message": job.error_message,
        "performance": performance,
        "artifact_counts": artifact_counts,
        "quality_checks": quality_checks,
    }


def seed_analysis_job(*, conversation_path: Path, self_display_name: str) -> tuple[int, int]:
    raw_bytes = conversation_path.read_bytes()
    parsed = parse_qq_export(raw_bytes.decode("utf-8"), self_display_name=self_display_name)
    other_display_name = next(
        (message.speaker_name for message in parsed.messages if message.speaker_role == "other"),
        "unknown",
    )
    with session_scope() as session:
        conversation = Conversation(
            title=parsed.chat_name or conversation_path.parent.name,
            chat_type="private",
            self_display_name=self_display_name,
            other_display_name=other_display_name,
            source_format="qq_chat_exporter_v5",
            status="queued",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name=conversation_path.name,
            source_file_path=str(conversation_path),
            source_file_hash=f"fixture:{conversation_path.parent.name}",
            message_count_hint=parsed.message_count_hint,
        )
        session.add(batch)
        session.flush()

        job = AnalysisJob(
            conversation_id=conversation.id,
            job_type="full_analysis",
            status="queued",
            current_stage="created",
            progress_percent=0,
            retry_count=0,
            payload_json={"import_id": batch.id},
        )
        session.add(job)
        session.flush()
        return conversation.id, job.id


def collect_analysis_artifacts(
    session,
    *,
    conversation_id: int,
    include_quality_checks: bool,
) -> tuple[dict[str, int], dict[str, Any] | None]:
    messages = session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.sequence_no.asc())
    ).scalars().all()
    segments = session.execute(
        select(Segment).where(Segment.conversation_id == conversation_id).order_by(Segment.id.asc())
    ).scalars().all()
    summaries = session.execute(
        select(SegmentSummary)
        .join(Segment, SegmentSummary.segment_id == Segment.id)
        .where(Segment.conversation_id == conversation_id)
        .order_by(SegmentSummary.id.asc())
    ).scalars().all()
    topics = session.execute(
        select(Topic).where(Topic.conversation_id == conversation_id).order_by(Topic.id.asc())
    ).scalars().all()
    topic_links = session.execute(
        select(TopicLink)
        .join(Topic, TopicLink.topic_id == Topic.id)
        .where(Topic.conversation_id == conversation_id)
        .order_by(TopicLink.id.asc())
    ).scalars().all()
    persona_profiles = session.execute(
        select(PersonaProfile)
        .where(PersonaProfile.conversation_id == conversation_id)
        .order_by(PersonaProfile.id.asc())
    ).scalars().all()
    snapshots = session.execute(
        select(RelationshipSnapshot)
        .where(RelationshipSnapshot.conversation_id == conversation_id)
        .order_by(RelationshipSnapshot.id.asc())
    ).scalars().all()

    counts = {
        "messages": len(messages),
        "segments": len(segments),
        "segment_summaries": len(summaries),
        "topics": len(topics),
        "topic_links": len(topic_links),
        "persona_profiles": len(persona_profiles),
        "relationship_snapshots": len(snapshots),
    }
    confidences = [float(summary.confidence) for summary in summaries]
    checks = None
    if include_quality_checks:
        checks = {
            "all_segments_have_summaries": len(summaries) == len(segments),
            "all_segments_have_snapshots": len(snapshots) == len(segments),
            "topic_links_cover_segments": len(topic_links) >= len(segments),
            "empty_segment_summary_count": sum(1 for summary in summaries if not summary.summary_text.strip()),
            "empty_snapshot_summary_count": sum(1 for snapshot in snapshots if not snapshot.snapshot_summary.strip()),
            "empty_topic_summary_count": sum(1 for topic in topics if not topic.topic_summary.strip()),
            "empty_persona_summary_count": sum(
                1 for persona in persona_profiles if not persona.global_persona_summary.strip()
            ),
            "segment_summary_confidence_min": round(min(confidences), 4) if confidences else None,
            "segment_summary_confidence_avg": round(sum(confidences) / len(confidences), 4) if confidences else None,
        }
    return counts, checks


def build_report(
    *,
    fixture_root: Path,
    run_root: Path,
    provider: dict[str, Any],
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = summarize_results(case_results)
    status = "completed_with_errors" if summary["error_case_count"] else "completed"
    return {
        "schema_version": SCHEMA_VERSION,
        "runner": RUNNER_NAME,
        "status": status,
        "generated_at_ms": int(time.time() * 1000),
        "fixture_root": _relative_path(fixture_root),
        "run_root": _relative_path(run_root),
        "provider": provider,
        "summary": summary,
        "cases": case_results,
    }


def summarize_results(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [case for case in case_results if case["status"] == "completed"]
    errors = [case for case in case_results if case["status"] == "error"]
    total_wall = round(sum(float(case["wall_clock_seconds"]) for case in completed), 3)
    total_messages = sum(int(case["message_count"]) for case in completed)
    total_segments = sum(int(case["segment_count"]) for case in completed)
    total_llm_calls = sum(
        int((case.get("performance", {}).get("llm_call_counts") or {}).get("total", 0))
        for case in completed
    )
    elapsed_samples = [
        float(case["performance"]["elapsed_seconds"])
        for case in completed
        if isinstance(case.get("performance", {}).get("elapsed_seconds"), int | float)
    ]
    return {
        "case_count": len(case_results),
        "completed_case_count": len(completed),
        "error_case_count": len(errors),
        "total_wall_clock_seconds": total_wall,
        "total_message_count": total_messages,
        "total_segment_count": total_segments,
        "total_llm_call_count": total_llm_calls,
        "max_case_elapsed_seconds": round(max(elapsed_samples), 3) if elapsed_samples else None,
        "avg_case_elapsed_seconds": round(sum(elapsed_samples) / len(elapsed_samples), 3) if elapsed_samples else None,
        "seconds_per_1000_messages": round((total_wall / total_messages) * 1000, 3) if total_messages else None,
    }


def build_markdown_report(report: dict[str, Any]) -> str:
    provider = report["provider"]
    summary = report["summary"]
    lines = [
        "# Synthetic Realism Full-Analysis Performance Report",
        "",
        f"Status: {report['status']}",
        f"Generated at ms: {report['generated_at_ms']}",
        f"Fixture root: {report['fixture_root']}",
        f"Run root: {report['run_root']}",
        f"Provider: {provider.get('status')} / {provider.get('source')} / {provider.get('role')} / {provider.get('model')}",
        "",
        "## Summary",
        "",
        f"- Cases: {summary['case_count']}",
        f"- Completed: {summary['completed_case_count']}",
        f"- Errors: {summary['error_case_count']}",
        f"- Total messages: {summary['total_message_count']}",
        f"- Total segments: {summary['total_segment_count']}",
        f"- Total wall clock seconds: {summary['total_wall_clock_seconds']}",
        f"- Total LLM calls: {summary['total_llm_call_count']}",
        f"- Seconds per 1000 messages: {summary['seconds_per_1000_messages']}",
        "",
        "## Cases",
        "",
        "| case | status | messages | segments | wall s | perf s | llm calls | topics | snapshots | worker log |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in report["cases"]:
        performance = case.get("performance") or {}
        llm_call_counts = performance.get("llm_call_counts") or {}
        artifact_counts = case.get("artifact_counts") or {}
        lines.append(
            "| {case_id} | {status} | {messages} | {segments} | {wall} | {perf} | {llm_calls} | {topics} | {snapshots} | {worker_log} |".format(
                case_id=_escape_md_cell(case["case_id"]),
                status=_escape_md_cell(case["status"]),
                messages=case["message_count"],
                segments=case["segment_count"],
                wall=case["wall_clock_seconds"],
                perf=performance.get("elapsed_seconds", "-"),
                llm_calls=llm_call_counts.get("total", 0),
                topics=artifact_counts.get("topics", 0),
                snapshots=artifact_counts.get("relationship_snapshots", 0),
                worker_log=_escape_md_cell(case["worker_log_path"]),
            )
        )
    return "\n".join(lines)


def write_report_files(
    *,
    report: dict[str, Any],
    run_root: Path,
    output_json: Path | None,
    output_markdown: Path | None,
) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    internal_json = run_root / "result.json"
    internal_markdown = run_root / "report.md"
    internal_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    internal_markdown.write_text(build_markdown_report(report), encoding="utf-8")

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
    parser = argparse.ArgumentParser(description="Run full-analysis performance sampling on committed realism fixtures.")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--self-display-name", default="我")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-markdown", type=Path, default=None)
    parser.add_argument("--analysis-llm-max-concurrency", type=int, default=None)
    parser.add_argument(
        "--require-provider",
        action="store_true",
        help="Return a non-zero exit code when worker provider configuration is missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    fixture_cases = discover_fixture_cases(
        args.fixture_root,
        case_ids=args.case_id,
        max_cases=args.max_cases,
    )
    run_root = args.run_root or (
        DEFAULT_RUNS_ROOT / f"realism-synthetic-{time.strftime('%Y%m%d-%H%M%S')}"
    )
    try:
        llm_client, provider = build_worker_client(env_file=args.env_file)
    except ProviderConfigError as exc:
        if args.require_provider:
            print(str(exc), file=sys.stderr)
            return 2
        report = build_report(
            fixture_root=args.fixture_root,
            run_root=run_root,
            provider={"status": "missing", "source": None, "role": PROVIDER_ROLE, "model": None, "api": None},
            case_results=[
                {
                    "case_id": case.case_id,
                    "status": "error",
                    "conversation_path": _relative_path(case.conversation_path),
                    "data_dir": None,
                    "worker_log_path": None,
                    "db_path": None,
                    "provider": {},
                    "message_count": 0,
                    "segment_count": 0,
                    "wall_clock_seconds": 0.0,
                    "job_status": "missing_provider",
                    "error_message": str(exc),
                    "performance": {},
                    "artifact_counts": {},
                    "quality_checks": {},
                }
                for case in fixture_cases
            ],
        )
    else:
        env_overrides: dict[str, str] = {}
        if args.analysis_llm_max_concurrency is not None:
            env_overrides["IF_THEN_ANALYSIS_LLM_MAX_CONCURRENCY"] = str(max(1, args.analysis_llm_max_concurrency))
        with _temporary_environment(env_overrides):
            report = run_fixture_analyses(
                fixture_cases=fixture_cases,
                llm_client=llm_client,
                provider=provider,
                run_root=run_root,
                self_display_name=args.self_display_name,
            )

    write_report_files(
        report=report,
        run_root=run_root,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
    )
    if args.output_json is None and args.output_markdown is None:
        print(build_markdown_report(report))

    if report["status"] == "completed_with_errors":
        return 1
    return 0


@contextmanager
def _temporary_environment(overrides: dict[str, str]):
    previous = {key: os.environ.get(key) for key in overrides}
    for key, value in overrides.items():
        os.environ[key] = value
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _relative_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _escape_md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
