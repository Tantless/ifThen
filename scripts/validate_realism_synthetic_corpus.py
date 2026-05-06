from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from if_then_mvp.parser import ParsedMessage, parse_qq_export


DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "realism_synthetic"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True, slots=True)
class FutureEvidenceRule:
    truth_id: str
    reveal_at: str
    terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RepeatedClueRule:
    clue: str
    max_count: int


@dataclass(frozen=True, slots=True)
class CaseRules:
    future_evidence: tuple[FutureEvidenceRule, ...] = ()
    repeated_clues: tuple[RepeatedClueRule, ...] = ()


@dataclass(frozen=True, slots=True)
class QualityFinding:
    key: str
    case_id: str
    check_id: str
    severity: str
    message: str
    timestamp: str | None = None
    content: str | None = None
    waived: bool = False
    waiver_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "key": self.key,
            "case_id": self.case_id,
            "check_id": self.check_id,
            "severity": self.severity,
            "message": self.message,
            "waived": self.waived,
        }
        if self.timestamp is not None:
            payload["timestamp"] = self.timestamp
        if self.content is not None:
            payload["content"] = self.content
        if self.waiver_reason is not None:
            payload["waiver_reason"] = self.waiver_reason
        return payload


CASE_RULES: dict[str, CaseRules] = {
    "case-01-hidden-trauma-confession": CaseRules(
        future_evidence=(
            FutureEvidenceRule(
                truth_id="T1",
                reveal_at="2026-04-23 17:44:27",
                terms=("以前那段关系", "一被确定就想逃"),
            ),
        ),
        repeated_clues=(RepeatedClueRule(clue="别对我太好", max_count=4),),
    ),
    "case-02-conflict-repair": CaseRules(
        future_evidence=(
            FutureEvidenceRule(
                truth_id="T1",
                reveal_at="2026-04-10 22:44:00",
                terms=("检查",),
            ),
        ),
    ),
    "case-03-missed-window": CaseRules(
        future_evidence=(
            FutureEvidenceRule(
                truth_id="T1",
                reveal_at="2026-04-19 23:02:30",
                terms=("不是随便问问",),
            ),
        ),
    ),
}


KNOWN_WAIVERS: dict[str, str] = {
    "case-01-hidden-trauma-confession:repeated-clue:别对我太好": (
        "Existing corpus over-signposts the hidden-trauma clue; keep visible until "
        "the fixture is regenerated or locally repaired."
    ),
    "case-02-conflict-repair:future-evidence-before-reveal:T1": (
        "Existing corpus mentions family-check evidence before the documented "
        "post-cutoff reveal; keep visible until the evidence ledger is rebuilt."
    ),
    "case-03-missed-window:early-sleep-cue:2026-03-26 19:23:25": (
        "Existing baseline targets this exact message, so keep the defect visible "
        "until baseline cases are migrated with a rewritten window."
    ),
}


def build_report(fixture_root: Path = DEFAULT_FIXTURE_ROOT) -> dict[str, Any]:
    findings: list[QualityFinding] = []
    case_dirs = [
        path
        for path in sorted(fixture_root.iterdir())
        if path.is_dir() and (path / "conversation.txt").exists()
    ]
    for case_dir in case_dirs:
        findings.extend(validate_case(case_dir))

    unwaived_count = sum(1 for finding in findings if not finding.waived)
    waived_count = len(findings) - unwaived_count
    return {
        "schema_version": 1,
        "fixture_root": _relative_path(fixture_root),
        "status": "passed" if unwaived_count == 0 else "failed",
        "summary": {
            "case_count": len(case_dirs),
            "finding_count": len(findings),
            "unwaived_finding_count": unwaived_count,
            "waived_finding_count": waived_count,
        },
        "findings": [finding.to_dict() for finding in findings],
    }


def validate_case(case_dir: Path) -> list[QualityFinding]:
    case_id = case_dir.name
    conversation_path = case_dir / "conversation.txt"
    text = conversation_path.read_text(encoding="utf-8")
    parsed = parse_qq_export(text, self_display_name="我")

    findings: list[QualityFinding] = []
    findings.extend(_check_export_time(case_id=case_id, text=text, messages=parsed.messages))
    findings.extend(_check_time_words(case_id=case_id, messages=parsed.messages))

    rules = CASE_RULES.get(case_id, CaseRules())
    findings.extend(_check_future_evidence(case_id=case_id, messages=parsed.messages, rules=rules.future_evidence))
    findings.extend(_check_repeated_clues(case_id=case_id, messages=parsed.messages, rules=rules.repeated_clues))
    return findings


def _check_export_time(*, case_id: str, text: str, messages: list[ParsedMessage]) -> list[QualityFinding]:
    export_time_raw = _extract_header_value(text, "导出时间")
    if export_time_raw is None:
        return [
            _finding(
                case_id=case_id,
                check_id="missing-export-time",
                marker="header",
                severity="high",
                message="conversation header is missing 导出时间",
            )
        ]
    if not messages:
        return []

    export_time = _parse_timestamp(export_time_raw)
    last_message_time = _parse_timestamp(messages[-1].timestamp)
    if export_time is None:
        return [
            _finding(
                case_id=case_id,
                check_id="invalid-export-time",
                marker="header",
                severity="high",
                message=f"导出时间 is not parseable: {export_time_raw}",
            )
        ]
    if last_message_time is not None and export_time < last_message_time:
        return [
            _finding(
                case_id=case_id,
                check_id="export-time-before-last-message",
                marker="header",
                severity="high",
                message=(
                    "导出时间 must be later than or equal to the final message timestamp "
                    f"({export_time_raw} < {messages[-1].timestamp})"
                ),
                timestamp=messages[-1].timestamp,
                content=messages[-1].content_text,
            )
        ]
    return []


def _check_time_words(*, case_id: str, messages: list[ParsedMessage]) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for message in messages:
        timestamp = _parse_timestamp(message.timestamp)
        if timestamp is None:
            continue
        content = message.content_text
        if timestamp.hour >= 12 and re.search(r"今天[^，。！？\n]*上午", content):
            findings.append(
                _finding(
                    case_id=case_id,
                    check_id="morning-reference-after-noon",
                    marker=message.timestamp,
                    severity="medium",
                    message="message says today/上午 after noon",
                    timestamp=message.timestamp,
                    content=content,
                )
            )
        if 6 <= timestamp.hour < 20 and "快睡" in content:
            findings.append(
                _finding(
                    case_id=case_id,
                    check_id="early-sleep-cue",
                    marker=message.timestamp,
                    severity="medium",
                    message="message uses sleep-closing wording before 20:00",
                    timestamp=message.timestamp,
                    content=content,
                )
            )
    return findings


def _check_future_evidence(
    *,
    case_id: str,
    messages: list[ParsedMessage],
    rules: tuple[FutureEvidenceRule, ...],
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for rule in rules:
        reveal_at = _parse_timestamp(rule.reveal_at)
        if reveal_at is None:
            continue
        matches: list[ParsedMessage] = []
        for message in messages:
            timestamp = _parse_timestamp(message.timestamp)
            if timestamp is None or timestamp >= reveal_at:
                continue
            if any(term in message.content_text for term in rule.terms):
                matches.append(message)
        if matches:
            first = matches[0]
            terms = " / ".join(rule.terms)
            findings.append(
                _finding(
                    case_id=case_id,
                    check_id="future-evidence-before-reveal",
                    marker=rule.truth_id,
                    severity="high",
                    message=(
                        f"truth {rule.truth_id} evidence terms appeared before reveal "
                        f"{rule.reveal_at}; terms={terms}; match_count={len(matches)}"
                    ),
                    timestamp=first.timestamp,
                    content=first.content_text,
                )
            )
    return findings


def _check_repeated_clues(
    *,
    case_id: str,
    messages: list[ParsedMessage],
    rules: tuple[RepeatedClueRule, ...],
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for rule in rules:
        matches = [message for message in messages if rule.clue in message.content_text]
        if len(matches) > rule.max_count:
            findings.append(
                _finding(
                    case_id=case_id,
                    check_id="repeated-clue",
                    marker=rule.clue,
                    severity="medium",
                    message=(
                        f"clue phrase appears {len(matches)} times, above max_count={rule.max_count}: "
                        f"{rule.clue}"
                    ),
                    timestamp=matches[0].timestamp,
                    content=matches[0].content_text,
                )
            )
    return findings


def _finding(
    *,
    case_id: str,
    check_id: str,
    marker: str,
    severity: str,
    message: str,
    timestamp: str | None = None,
    content: str | None = None,
) -> QualityFinding:
    key = f"{case_id}:{check_id}:{marker}"
    waiver_reason = KNOWN_WAIVERS.get(key)
    return QualityFinding(
        key=key,
        case_id=case_id,
        check_id=check_id,
        severity=severity,
        message=message,
        timestamp=timestamp,
        content=content,
        waived=waiver_reason is not None,
        waiver_reason=waiver_reason,
    )


def _extract_header_value(text: str, header_name: str) -> str | None:
    prefix = f"{header_name}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate synthetic realism fixture quality.")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args.fixture_root)
    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_json:
        args.output_json.write_text(report_json + "\n", encoding="utf-8")
    else:
        print(report_json)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
