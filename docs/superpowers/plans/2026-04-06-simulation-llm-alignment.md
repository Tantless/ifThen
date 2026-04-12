# Simulation LLM Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder simulation logic with real LLM-driven branch assessment, first-reply generation, and iterative short-thread simulation.

**Architecture:** Keep the existing `/simulations` API surface and persistence model, but inject a real chat JSON client into the simulation layer. The simulation engine will consume the existing `ContextPack`, call the model for structured branch assessment, then generate a first reply and additional turns one-by-one while updating branch state and stopping early on repetition.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, OpenAI-compatible chat JSON client, pytest

---

## 执行状态（2026-04-08 同步）

- 状态：**已完成并已并入 `main`**
- 结果：`/simulations` 已切换为真实 LLM 分支判断、首轮回复生成与短链续写流程，相关测试已纳入主分支回归。
- 当前验证参考：`python -m pytest -q` 在 `main` 上为 `71 passed`。
- 说明：下方 `- [ ]` 复选框保留为原始执行脚本，不再表示当前待办；当前总体进度以 `docs/project-status.md` 为准。

## File Structure

- `src/if_then_mvp/api.py`
  - Inject simulation LLM dependencies and call the new simulation flow.
- `src/if_then_mvp/simulation.py`
  - Add structured simulation payload models, prompt builders, iterative turn generation, and repetition detection.
- `src/if_then_mvp/llm.py`
  - Reuse existing typed JSON client without transport changes.
- `tests/test_simulations.py`
  - Add failing tests for real simulation LLM usage, prompt grounding, first-turn alignment, and repetition stop.
- `README.md`
  - Document that `/simulations` now requires LLM runtime config.

## Task 1: Add failing simulation tests

- [ ] Assert `/simulations` uses an injected fake LLM for branch assessment, first reply, and next turns.
- [ ] Assert simulation prompts contain persona, related topic, and current-state evidence.
- [ ] Assert `simulated_turns[0].message_text == first_reply_text`.
- [ ] Assert repeated generated content stops the short thread early.

## Task 2: Implement LLM-driven simulation engine

- [ ] Add structured Pydantic payloads for branch assessment, first reply, turn state, and next turn.
- [ ] Replace placeholder branching logic with typed LLM calls.
- [ ] Build prompt serializers that include cutoff-safe context, personas, topics, state, and transcript.
- [ ] Make short-thread generation advance one turn at a time and update branch state after each turn.
- [ ] Stop early when the model asks to stop or when repeated output is detected.

## Task 3: Wire `/simulations` to runtime LLM configuration

- [ ] Allow `create_app()` to accept an injected simulation LLM for tests.
- [ ] Load LLM settings for runtime from `app_settings`, falling back to environment variables.
- [ ] Return a clear API error when simulation LLM config is unavailable.

## Task 4: Update docs and verify

- [ ] Add a short README note describing required simulation LLM config.
- [ ] Run focused simulation tests.
- [ ] Run full pytest suite.
