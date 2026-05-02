from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

from if_then_mvp.parser import parse_qq_export


BASELINE_PATH = Path("tests/fixtures/realism_baseline/cases.json")
SYNTHETIC_ROOT = Path("tests/fixtures/realism_synthetic")
REQUIRED_FAILURE_TYPES = {
    "over_optimistic_shift",
    "future_fact_blindness",
    "future_fact_leakage",
    "persona_mismatch",
    "style_mismatch",
    "retrieval_miss",
    "short_thread_incoherence",
    "relationship_state_jump",
}
PII_PATTERN = re.compile(r"https?://|www\.|微信号|QQ号|手机号|身份证", flags=re.IGNORECASE)
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


def _load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def test_realism_baseline_contract_and_failure_coverage():
    payload = _load_baseline()
    cases = payload["cases"]
    taxonomy = set(payload["failure_taxonomy"])

    assert payload["schema_version"] == 1
    assert payload["capture_method"] == "curated_current_failure_snapshot"
    assert len(cases) >= 10
    assert taxonomy == REQUIRED_FAILURE_TYPES
    assert len({case["id"] for case in cases}) == len(cases)

    covered_failure_types = {
        annotation["type"]
        for case in cases
        for annotation in case["failure_annotations"]
    }
    assert REQUIRED_FAILURE_TYPES <= covered_failure_types

    for case in cases:
        assert case["source_fixture"]
        assert case["scenario"]
        assert case["expected_risk"] in {"low", "medium", "high"}
        assert case["target"]["speaker_role"] == "self"
        assert case["target"]["sequence_no"] > 0
        assert case["target"]["cutoff_timestamp"]
        assert case["target"]["original_text"]
        assert case["rewrite_text"]

        modeler_evidence = case["modeler_only_evidence"]
        assert modeler_evidence["not_character_known_at_cutoff"] is True
        assert modeler_evidence["truth_digest"]
        assert modeler_evidence["evidence_anchor"]
        assert modeler_evidence["forbidden_character_knowledge"]

        current_output = case["current_output"]
        assert current_output["branch_direction"]
        assert current_output["branch_assessment_summary"]
        assert current_output["first_reply_text"]
        assert current_output["short_thread_turns"]
        assert current_output["state_after_turn"]

        assert case["failure_annotations"]
        for annotation in case["failure_annotations"]:
            assert annotation["type"] in taxonomy
            assert annotation["severity"] in ALLOWED_SEVERITIES
            assert annotation["note"]

        assert not PII_PATTERN.search(json.dumps(case, ensure_ascii=False))


def test_realism_baseline_targets_existing_synthetic_messages():
    payload = _load_baseline()
    parsed_by_fixture = {}

    for case in payload["cases"]:
        source_fixture = case["source_fixture"]
        if source_fixture not in parsed_by_fixture:
            conversation_path = SYNTHETIC_ROOT / source_fixture / "conversation.txt"
            parsed_by_fixture[source_fixture] = parse_qq_export(
                conversation_path.read_text(encoding="utf-8"),
                self_display_name="我",
            )

        parsed = parsed_by_fixture[source_fixture]
        target = case["target"]
        message = parsed.messages[target["sequence_no"] - 1]

        assert message.speaker_role == "self"
        assert message.timestamp == target["cutoff_timestamp"]
        assert message.content_text == target["original_text"]


def test_future_leakage_cases_are_explicitly_labeled():
    payload = _load_baseline()

    for case in payload["cases"]:
        output_text = json.dumps(case["current_output"], ensure_ascii=False)
        forbidden_terms = case["modeler_only_evidence"]["forbidden_character_knowledge"]
        output_contains_future_term = any(term in output_text for term in forbidden_terms)
        is_leakage_case = any(
            annotation["type"] == "future_fact_leakage"
            for annotation in case["failure_annotations"]
        )

        assert output_contains_future_term is is_leakage_case


def test_realism_baseline_report_script_outputs_summary():
    result = subprocess.run(
        [sys.executable, "scripts/report_realism_baseline.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    output = result.stdout
    assert "# Realism Baseline Report" in output
    assert "Total cases: 12" in output
    for failure_type in REQUIRED_FAILURE_TYPES:
        assert failure_type in output
