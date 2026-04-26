# 5000 Message Analysis Performance Run

Date: 2026-04-26

This report is based on one real worker run against `聊天记录-5000条.txt` from the MVP test dataset. The run used an isolated data directory, so it did not modify the app's normal `.data` database.

## Run Setup

| Item | Value |
| --- | --- |
| Dataset | `聊天记录-5000条.txt` |
| File size | 446,350 bytes |
| Declared messages | 5,000 |
| Parsed messages | 5,000 |
| Time range | 2025-03-02 20:18:03 to 2025-03-09 23:53:47 |
| Segments | 47 |
| Model | `gpt-5.4-mini` |
| Provider host | `new.myouo.online` |
| Isolated data dir | `.data/perf-runs/analysis-5000-20260426-155914/app-data` |
| Raw log | `.data/perf-runs/analysis-5000-20260426-155914/worker.log` |
| Raw result JSON | `.data/perf-runs/analysis-5000-20260426-155914/result.json` |

The worker job completed successfully.

## Result Summary

| Metric | Value |
| --- | ---: |
| Worker wall time | 1204.812 s |
| Persisted performance elapsed | 1204.800 s |
| Total LLM calls | 157 |
| Average elapsed per LLM call, whole job | 7.674 s |
| Messages persisted | 5,000 |
| Segment summaries | 47 |
| Topics | 13 |
| Topic links | 61 |
| Persona profiles | 2 |
| Relationship snapshots | 47 |

## Stage Timing

| Stage | Seconds | Share |
| --- | ---: | ---: |
| topic_resolution | 446.489 | 37.06% |
| summarizing | 374.135 | 31.05% |
| snapshots | 330.114 | 27.40% |
| persona | 29.561 | 2.45% |
| topic_merge_review | 24.061 | 2.00% |
| parsing | 0.427 | 0.04% |
| segmenting | 0.009 | 0.00% |
| finalizing | 0.000 | 0.00% |

The top three stages, `topic_resolution`, `summarizing`, and `snapshots`, used 1150.738 seconds, or 95.51% of total measured time.

## LLM Call Counts

| Call type | Calls | Related stage | Approx stage avg |
| --- | ---: | --- | ---: |
| segment_summary | 47 | summarizing | 7.960 s/call |
| topic_assignment | 47 | topic_resolution | included below |
| topic_creation | 13 | topic_resolution | 7.441 s/call across assignment + creation |
| topic_merge_review | 1 | topic_merge_review | 24.061 s/call |
| persona | 2 | persona | 14.781 s/call |
| relationship_snapshot | 47 | snapshots | 7.024 s/call |

The job is dominated by serial LLM calls. Parsing 5,000 messages and writing them to SQLite took less than half a second in this run.

## Segment Shape

| Metric | Value |
| --- | ---: |
| Segment count | 47 |
| Min messages per segment | 2 |
| Max messages per segment | 1,177 |
| Average messages per segment | 106.383 |
| Median messages per segment | 42 |
| P90 messages per segment | 251.6 |

All 47 persisted segments were `normal`.

## What This Explains

The measured bottleneck is not raw file parsing, message insertion, or segment materialization. The measured bottleneck is the number of serialized model calls after segmentation.

For this dataset, 47 segments caused 157 LLM calls:

- 47 calls to summarize segments.
- 60 calls for topic resolution: 47 assignments plus 13 new-topic creations.
- 1 call for topic merge review.
- 2 calls for persona generation.
- 47 calls for relationship snapshots.

This also explains why long chats feel slow: once the conversation is split into many segments, the current worker mostly processes those segments one by one. Even when each call averages only around 7 to 8 seconds, hundreds of calls accumulate into a long wait.

Do not treat this 5,000-message run as a precise linear prediction for 100,000 messages. Segment count depends on the actual chat timeline, gaps, and message density. Topic creation counts also depend on content. But the measured mechanism is clear: runtime tracks serialized LLM work much more than raw message count.

## Important Progress Issue

The worker reached `97%` overall progress at about 0.4 seconds, immediately after parsing and segmenting. The job still had about 20 minutes of model work remaining.

This is because the current progress formula weights raw message parsing heavily, while parsing is extremely cheap in wall time. For user-facing progress, this is misleading. Progress should be reweighted around expected LLM work or displayed as stage-specific progress with clearer wording.

## Optimization Priority From This Run

1. First target: topic resolution.

   It was the largest measured stage at 446.489 seconds. The current design performs one topic assignment per segment, with extra topic creation calls when needed. Reducing call count here has high leverage.

2. Second target: segment summarization.

   It used 374.135 seconds for 47 serial calls. Any safe batching or concurrency strategy here can materially reduce wait time, but the current `previous_snapshot_summary` dependency must be handled deliberately.

3. Third target: relationship snapshots.

   It used 330.114 seconds for 47 serial calls. This stage is sequential because every snapshot uses the prior snapshot summary. A practical optimization may be reducing snapshot frequency or creating event-based snapshots rather than snapshotting every segment.

4. Also fix perceived progress.

   Even before reducing total time, progress reporting should stop showing near-complete status before the expensive LLM stages start.

## Evidence Files

- Raw worker log: `.data/perf-runs/analysis-5000-20260426-155914/worker.log`
- Raw result JSON: `.data/perf-runs/analysis-5000-20260426-155914/result.json`
- Isolated SQLite database: `.data/perf-runs/analysis-5000-20260426-155914/app-data/db/if_then_mvp.sqlite3`
