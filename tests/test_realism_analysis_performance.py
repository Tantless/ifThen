from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_realism_analysis_performance.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_realism_analysis_performance", RUNNER_PATH)
assert RUNNER_SPEC is not None
assert RUNNER_SPEC.loader is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)


class FakeLLM:
    def chat_json(self, *, system_prompt, user_prompt, response_model):
        payload_map = {
            "summary_text": "这是一次轻松的开场互动。",
            "main_topics": ["开场聊天"],
            "self_stance": "积极回应",
            "other_stance": "轻松开启聊天",
            "emotional_tone": "轻松",
            "interaction_pattern": "日常互动",
            "has_conflict": False,
            "has_repair": False,
            "has_closeness_signal": False,
            "outcome": "继续聊天",
            "relationship_impact": "neutral_positive",
            "confidence": 0.8,
            "matched_topics": [{"topic_id": 1, "link_reason": "当前段延续既有开场互动。", "score": 0.9}],
            "should_create_new_topic": False,
            "topic_name": "开场聊天",
            "topic_summary": "双方在建立联系。",
            "topic_status": "ongoing",
            "relevance_reason": "段摘要高度相似",
            "merges": [],
            "global_persona_summary": "表达轻松，回应直接。",
            "style_traits": ["简短", "口语化"],
            "conflict_traits": ["先解释后回避"],
            "relationship_specific_patterns": ["会主动接梗"],
            "relationship_temperature": "warm",
            "tension_level": "low",
            "openness_level": "medium",
            "initiative_balance": "balanced",
            "defensiveness_level": "low",
            "unresolved_conflict_flags": [],
            "relationship_phase": "warming",
            "snapshot_summary": "双方刚建立联系，整体轻松。",
        }
        return response_model(**{key: value for key, value in payload_map.items() if key in response_model.model_fields})


def test_discover_fixture_cases_filters_and_limits(tmp_path):
    case_a = tmp_path / "case-a"
    case_b = tmp_path / "case-b"
    case_a.mkdir()
    case_b.mkdir()
    (case_a / "conversation.txt").write_text("a", encoding="utf-8")
    (case_b / "conversation.txt").write_text("b", encoding="utf-8")

    cases = runner.discover_fixture_cases(tmp_path, case_ids=["case-b"], max_cases=1)

    assert [case.case_id for case in cases] == ["case-b"]


def test_run_case_analysis_collects_artifacts_and_logs(tmp_path, monkeypatch):
    monkeypatch.delenv("IF_THEN_DATA_DIR", raising=False)
    fixture_root = tmp_path / "fixtures"
    case_dir = fixture_root / "case-a"
    case_dir.mkdir(parents=True)
    conversation_path = case_dir / "conversation.txt"
    conversation_path.write_bytes(Path("tests/fixtures/qq_export_sample.txt").read_bytes())
    run_root = tmp_path / "perf-run"

    result = runner.run_case_analysis(
        case=runner.FixtureCase(case_id="case-a", conversation_path=conversation_path),
        llm_client=FakeLLM(),
        run_root=run_root,
        self_display_name="Tantless",
        provider={"status": "configured", "source": "fake", "role": "worker", "model": "fake-model", "api": "chat_completions"},
    )

    assert result["status"] == "completed"
    assert result["job_status"] == "completed"
    assert result["artifact_counts"]["messages"] > 0
    assert result["artifact_counts"]["segments"] > 0
    assert result["artifact_counts"]["segment_summaries"] == result["artifact_counts"]["segments"]
    assert result["quality_checks"]["all_segments_have_summaries"] is True
    assert (run_root / "case-a" / "worker.log").exists()


def test_main_writes_report_files_with_patched_worker_client(tmp_path, monkeypatch):
    fixture_root = tmp_path / "fixtures"
    case_dir = fixture_root / "case-a"
    case_dir.mkdir(parents=True)
    (case_dir / "conversation.txt").write_bytes(Path("tests/fixtures/qq_export_sample.txt").read_bytes())
    run_root = tmp_path / "perf-run"
    output_json = tmp_path / "report.json"
    output_markdown = tmp_path / "report.md"

    monkeypatch.setattr(
        runner,
        "build_worker_client",
        lambda env_file: (
            FakeLLM(),
            {
                "status": "configured",
                "source": "fake",
                "role": "worker",
                "model": "fake-model",
                "api": "chat_completions",
            },
        ),
    )

    exit_code = runner.main(
        [
            "--fixture-root",
            str(fixture_root),
            "--self-display-name",
            "Tantless",
            "--run-root",
            str(run_root),
            "--output-json",
            str(output_json),
            "--output-markdown",
            str(output_markdown),
        ]
    )

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report["status"] == "completed"
    assert report["summary"]["case_count"] == 1
    assert report["summary"]["completed_case_count"] == 1
    assert (run_root / "result.json").exists()
    assert (run_root / "report.md").exists()
    assert "Synthetic Realism Full-Analysis Performance Report" in output_markdown.read_text(encoding="utf-8")
