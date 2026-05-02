from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


BASELINE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "realism_baseline" / "cases.json"


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(payload: dict[str, Any]) -> str:
    cases = payload["cases"]
    taxonomy = payload["failure_taxonomy"]
    coverage = Counter(
        annotation["type"]
        for case in cases
        for annotation in case["failure_annotations"]
    )
    scenario_counts = Counter(case["scenario"] for case in cases)

    lines = [
        "# Realism Baseline Report",
        "",
        f"Total cases: {len(cases)}",
        "",
        "## Scenario Coverage",
    ]
    for scenario, count in sorted(scenario_counts.items()):
        lines.append(f"- {scenario}: {count}")

    lines.extend(["", "## Failure Coverage"])
    for failure_type, label in taxonomy.items():
        lines.append(f"- {failure_type} ({label}): {coverage[failure_type]}")

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| id | source | cutoff | risk | failures |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for case in cases:
        failures = ", ".join(annotation["type"] for annotation in case["failure_annotations"])
        lines.append(
            "| {id} | {source} | {cutoff} | {risk} | {failures} |".format(
                id=case["id"],
                source=case["source_fixture"],
                cutoff=case["target"]["cutoff_timestamp"],
                risk=case["expected_risk"],
                failures=failures,
            )
        )

    return "\n".join(lines)


def main() -> None:
    print(build_report(load_baseline()))


if __name__ == "__main__":
    main()
