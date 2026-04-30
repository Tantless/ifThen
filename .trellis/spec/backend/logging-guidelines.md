# Logging Guidelines

> How logging is done in this project.

---

## Overview

<!--
Document your project's logging conventions here.

Questions to answer:
- What logging library do you use?
- What are the log levels and when to use each?
- What should be logged?
- What should NOT be logged (PII, secrets)?
-->

(To be filled by the team)

---

## Log Levels

<!-- When to use each level: debug, info, warn, error -->

(To be filled by the team)

---

## Structured Logging

<!-- Log format, required fields -->

(To be filled by the team)

---

## What to Log

<!-- Important events to log -->

(To be filled by the team)

## Analysis Job Performance Diagnostics

### Scope / Trigger

Use this pattern when changing `src/if_then_mvp/worker.py` analysis-job stages or adding long-running worker steps. Diagnostics must be non-PII and must explain why an analysis job takes time.

### Contract

`AnalysisJob.payload_json["performance"]` is the persisted diagnostic object for full-analysis and import-only jobs.

Fields:

```python
{
    "elapsed_seconds": float,
    "current_stage": str | None,
    "input_counts": {
        "messages": int,
        "segments": int,
    },
    "llm_call_counts": {
        "segment_summary": int,
        "topic_assignment": int,
        "topic_creation": int,
        "topic_merge_review": int,
        "persona": int,
        "relationship_snapshot": int,
        "total": int,
    },
    "stage_elapsed_seconds": {
        "parsing": float,
        "segmenting": float,
        "summarizing": float,
        "topic_resolution": float,
        "topic_merge_review": float,
        "persona": float,
        "snapshots": float,
        "finalizing": float,
    },
}
```

Not every key is guaranteed to exist in partial or failed jobs. Consumers must treat missing operation or stage keys as zero/unknown.

### Required Tests

When changing analysis stages, update `tests/test_worker.py::test_run_next_job_records_analysis_performance_diagnostics` to assert:

* input counts match the fixture;
* LLM operation counts match the actual calls;
* stage elapsed seconds are attributed to the intended stage;
* console progress still includes elapsed seconds for analysis snapshots.

### Wrong vs Correct

Wrong:

```python
payload_json["performance"] = {"slow": True, "notes": raw_prompt_text}
```

Correct:

```python
payload_json["performance"] = {
    "elapsed_seconds": 88.0,
    "input_counts": {"messages": 6, "segments": 3},
    "llm_call_counts": {"segment_summary": 3, "total": 13},
    "stage_elapsed_seconds": {"summarizing": 6.0},
}
```

---

## What NOT to Log

<!-- Sensitive data, PII, secrets -->

(To be filled by the team)

Do not log or persist raw message text, prompts, API keys, model responses, user names, or exported chat file paths in performance diagnostics. Counts, stage names, and elapsed seconds are safe.
