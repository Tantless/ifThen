# Simulation Job Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把同步 `/simulations` 改造成持久化的异步 simulation job 体系，让后端提供真实阶段进度，前端轮询最新 job，只在完成后一次性展示最终推演结果。

**Architecture:** 后端新增独立 `simulation_jobs` 实体与序列化/取消/进度 helper，`POST /simulations` 改为返回 `SimulationJobRead`，worker 在现有进程内增加 simulation lane 处理 job 并在完成后写入 `simulations`/`simulation_turns`。桌面端把当前“直接 await 最终 simulation”改成“提交 job -> 轮询最新 job -> 完成后拉最终结果”，并用最新请求 token 防止旧 job 覆盖新 UI 状态。

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, React, TypeScript, Vitest

---

## File Map

### New files to create

- `src/if_then_mvp/simulation_jobs.py`
  - simulation job 的创建、取消、序列化、进度写入、claim helper
- `desktop/src/lib/simulationJobProgress.ts`
  - simulation job 阶段文案和进度条映射
- `desktop/tests/simulationJobProgress.test.ts`
  - simulation job 阶段文案单测

### Existing files to modify

- `src/if_then_mvp/models.py`
  - 新增 `SimulationJob` ORM 模型
- `src/if_then_mvp/schemas.py`
  - 新增 `SimulationJobRead`
- `src/if_then_mvp/api.py`
  - `/simulations` 改为异步 job 创建
  - 新增 simulation job 查询和最终 simulation 读取接口
- `src/if_then_mvp/worker.py`
  - 新增 simulation worker lane、软取消检查、最终结果落库
- `tests/test_simulations.py`
  - 把同步 `/simulations` 断言改为 async job 契约断言
- `tests/test_worker.py`
  - 为 simulation worker lane、取消、完成结果关联补测试
- `desktop/src/types/api.ts`
  - 新增 `SimulationJobRead`
- `desktop/src/lib/services/simulationService.ts`
  - 改为“创建 job + 读 job + 列 conversation jobs + 读最终 simulation”
- `desktop/src/lib/chatState.ts`
  - 增加 simulation job 请求 token/最新请求校验 helper
- `desktop/src/App.tsx`
  - 改写 rewrite submit / pending / polling / recovery / latest-wins 状态机
- `desktop/tests/visualShell.test.tsx`
  - 把同步推演测试改为异步 job 轮询与最终读取

### Files explicitly out of scope

- `desktop/electron/**`
- `scripts/run_api.py`
- `scripts/run_worker.py`
- SSE / WebSocket
- 中间推演文本流式展示

---

### Task 1: Queue Simulation Jobs Instead Of Blocking `/simulations`

**Files:**
- Create: `src/if_then_mvp/simulation_jobs.py`
- Modify: `src/if_then_mvp/models.py`
- Modify: `src/if_then_mvp/schemas.py`
- Modify: `src/if_then_mvp/api.py`
- Test: `tests/test_simulations.py`

- [ ] **Step 1: Write the failing backend contract tests for queued simulation jobs**

Add these tests near the top of `tests/test_simulations.py` after the helper classes:

```python
from if_then_mvp.models import SimulationJob


def test_post_simulations_returns_queued_job_and_latest_job_list(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="ready",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=2,
        )
        session.add(batch)
        session.flush()

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="在吗",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="在的",
                    message_type="text",
                ),
            ]
        )
        session.flush()

        session.add(
            Segment(
                conversation_id=conversation.id,
                start_message_id=1,
                end_message_id=2,
                start_time="2025-03-02T20:18:03",
                end_time="2025-03-02T20:18:04",
                message_count=2,
                self_message_count=1,
                other_message_count=1,
                segment_kind="normal",
                source_message_ids=[1, 2],
            )
        )

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 2,
                "replacement_content": "如果你不忙，我们慢慢说也可以",
                "mode": "short_thread",
                "turn_count": 4,
            },
        )
        list_response = client.get("/conversations/1/simulation-jobs?limit=1")

    assert create_response.status_code == 202
    body = create_response.json()
    assert body["status"] == "queued"
    assert body["current_stage"] == "queued"
    assert body["progress_percent"] == 0
    assert body["result_simulation_id"] is None

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == body["id"]

    with session_scope() as session:
        job = session.query(SimulationJob).one()
        assert job.status == "queued"
        assert job.current_stage == "queued"
        assert job.result_simulation_id is None
```

- [ ] **Step 2: Run the focused backend test to verify it fails under the current synchronous API**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_simulations.py::test_post_simulations_returns_queued_job_and_latest_job_list -q
```

Expected:
- FAIL
- Current failure should show that `POST /simulations` still returns `201` and `SimulationRead`, and `/conversations/{id}/simulation-jobs` does not exist yet

- [ ] **Step 3: Implement `SimulationJob`, `SimulationJobRead`, queue creation helpers, and the new queue/list endpoints**

Create `src/if_then_mvp/simulation_jobs.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from if_then_mvp.models import SimulationJob
from if_then_mvp.schemas import SimulationJobRead


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def simulation_job_to_read(job: SimulationJob) -> SimulationJobRead:
    progress = (job.payload_json or {}).get("progress", {})
    current_stage_total_units = int(progress.get("current_stage_total_units", 0) or 0)
    current_stage_completed_units = int(progress.get("current_stage_completed_units", 0) or 0)
    overall_total_units = int(progress.get("overall_total_units", 0) or 0)
    overall_completed_units = int(progress.get("overall_completed_units", 0) or 0)

    current_stage_percent = 0
    if current_stage_total_units > 0:
        current_stage_percent = min(100, int((current_stage_completed_units * 100) / current_stage_total_units))

    return SimulationJobRead(
        id=job.id,
        conversation_id=job.conversation_id,
        target_message_id=job.target_message_id,
        mode=job.mode,
        turn_count=job.turn_count,
        replacement_content=job.replacement_content,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        current_stage_percent=current_stage_percent,
        current_stage_total_units=current_stage_total_units,
        current_stage_completed_units=current_stage_completed_units,
        overall_total_units=overall_total_units,
        overall_completed_units=overall_completed_units,
        status_message=progress.get("status_message"),
        result_simulation_id=job.result_simulation_id,
        error_message=job.error_message,
    )


def list_simulation_jobs_for_conversation(session, *, conversation_id: int, limit: int) -> list[SimulationJob]:
    return (
        session.execute(
            select(SimulationJob)
            .where(SimulationJob.conversation_id == conversation_id)
            .order_by(SimulationJob.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
```

Add this model to `src/if_then_mvp/models.py`:

```python
class SimulationJob(TimestampMixin, Base):
    __tablename__ = "simulation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    target_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False)
    replacement_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_simulation_id: Mapped[int | None] = mapped_column(ForeignKey("simulations.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Add this schema to `src/if_then_mvp/schemas.py`:

```python
class SimulationJobRead(BaseModel):
    id: int
    conversation_id: int
    target_message_id: int
    mode: str
    turn_count: int
    replacement_content: str
    status: str
    current_stage: str
    progress_percent: int
    current_stage_percent: int = 0
    current_stage_total_units: int = 0
    current_stage_completed_units: int = 0
    overall_total_units: int = 0
    overall_completed_units: int = 0
    status_message: str | None = None
    result_simulation_id: int | None = None
    error_message: str | None = None
```

In `src/if_then_mvp/api.py`, change `POST /simulations` and add the conversation list endpoint:

```python
from if_then_mvp.models import SimulationJob
from if_then_mvp.schemas import SimulationJobRead
from if_then_mvp.simulation_jobs import list_simulation_jobs_for_conversation, simulation_job_to_read


@app.post("/simulations", response_model=SimulationJobRead, status_code=202)
def create_simulation(payload: SimulationCreate) -> SimulationJobRead:
    with session_scope() as session:
        _require_conversation(session, payload.conversation_id)
        target_message = session.get(Message, payload.target_message_id)
        if target_message is None or target_message.conversation_id != payload.conversation_id:
            raise HTTPException(status_code=404, detail="Target message not found")

        job = SimulationJob(
            conversation_id=payload.conversation_id,
            target_message_id=payload.target_message_id,
            mode=payload.mode,
            turn_count=payload.turn_count,
            replacement_content=payload.replacement_content,
            status="queued",
            current_stage="queued",
            progress_percent=0,
            payload_json={
                "progress": {
                    "current_stage_total_units": 1,
                    "current_stage_completed_units": 0,
                    "overall_total_units": 1,
                    "overall_completed_units": 0,
                    "status_message": "queued 0/1 steps",
                }
            },
        )
        session.add(job)
        session.flush()
        return simulation_job_to_read(job)


@app.get("/conversations/{conversation_id}/simulation-jobs", response_model=list[SimulationJobRead])
def list_simulation_jobs(conversation_id: int, limit: int = Query(default=10, ge=1, le=50)) -> list[SimulationJobRead]:
    with session_scope() as session:
        _require_conversation(session, conversation_id)
        rows = list_simulation_jobs_for_conversation(session, conversation_id=conversation_id, limit=limit)
        return [simulation_job_to_read(item) for item in rows]
```

- [ ] **Step 4: Run the focused backend test again and verify it passes**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_simulations.py::test_post_simulations_returns_queued_job_and_latest_job_list -q
```

Expected:
- PASS
- The test should show `1 passed`

- [ ] **Step 5: Commit the queue-contract slice**

```powershell
git add src/if_then_mvp/models.py src/if_then_mvp/schemas.py src/if_then_mvp/api.py src/if_then_mvp/simulation_jobs.py tests/test_simulations.py
git commit -m "Queue simulation jobs instead of blocking the API response" -m "The simulation endpoint now creates persistent jobs and exposes a conversation-scoped job listing endpoint, so the desktop client can observe execution state without seeing intermediate branch content.

Constraint: Frontend may display only progress metadata and final results, not partial simulation output
Rejected: Reuse analysis_jobs for simulation progress | would mix two job domains and complicate filtering
Confidence: high
Scope-risk: moderate
Directive: Keep simulation execution state in simulation_jobs; do not leak branch text into job payloads
Tested: python -m pytest tests/test_simulations.py::test_post_simulations_returns_queued_job_and_latest_job_list -q
Not-tested: Worker execution, cancellation, or desktop integration"
```

---

### Task 2: Execute Queued Simulation Jobs And Expose Final Results

**Files:**
- Modify: `src/if_then_mvp/worker.py`
- Modify: `src/if_then_mvp/api.py`
- Modify: `src/if_then_mvp/simulation_jobs.py`
- Modify: `tests/test_simulations.py`
- Modify: `tests/test_worker.py`

- [ ] **Step 1: Write the failing worker + final-result API tests**

Add this worker test to `tests/test_worker.py`:

```python
from if_then_mvp.models import Simulation, SimulationJob, SimulationTurn
from if_then_mvp.worker import run_next_simulation_job
from if_then_mvp.simulation import BranchAssessmentPayload, FirstReplyPayload, NextTurnPayload, TurnStatePayload


class FakeSimulationLLM:
    def __init__(self, responses):
        self._responses = responses

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        response = self._responses.pop(0)
        assert isinstance(response, response_model)
        return response


def test_run_next_simulation_job_persists_final_result_and_links_job(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="ready",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=2,
        )
        session.add(batch)
        session.flush()

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="在吗",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="在的",
                    message_type="text",
                ),
            ]
        )
        session.flush()

        session.add(
            Segment(
                conversation_id=conversation.id,
                start_message_id=1,
                end_message_id=2,
                start_time="2025-03-02T20:18:03",
                end_time="2025-03-02T20:18:04",
                message_count=2,
                self_message_count=1,
                other_message_count=1,
                segment_kind="normal",
                source_message_ids=[1, 2],
            )
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=1,
                as_of_time="2025-03-02T20:18:03",
                relationship_temperature="warm",
                tension_level="low",
                openness_level="medium",
                initiative_balance="balanced",
                defensiveness_level="low",
                unresolved_conflict_flags=[],
                relationship_phase="warming",
                snapshot_summary="轻松的开场互动",
            )
        )
        session.add(
            SimulationJob(
                conversation_id=conversation.id,
                target_message_id=2,
                mode="short_thread",
                turn_count=3,
                replacement_content="如果你不忙，我们慢慢说也可以",
                status="queued",
                current_stage="queued",
                progress_percent=0,
                payload_json={"progress": {"current_stage_total_units": 4, "current_stage_completed_units": 0, "overall_total_units": 4, "overall_completed_units": 0, "status_message": "queued 0/4 steps"}},
            )
        )

    processed = run_next_simulation_job(
        llm_client=FakeSimulationLLM(
            [
                BranchAssessmentPayload(
                    branch_direction="closer",
                    state_shift_summary="新说法缓和了互动压力。",
                    other_immediate_feeling="更放松",
                    reply_strategy="light_follow_up",
                    risk_flags=[],
                    confidence=0.8,
                ),
                FirstReplyPayload(
                    first_reply_text="好，那晚点聊也没事。",
                    strategy_used="light_follow_up",
                    first_reply_style_notes="先低压力接住。",
                    state_after_turn=TurnStatePayload(
                        relationship_temperature="warm",
                        tension_level="low",
                        openness_level="medium",
                        initiative_balance="balanced",
                        defensiveness_level="low",
                        relationship_phase="warming",
                        active_sensitive_topics=[],
                        state_rationale="轻微缓和。",
                    ),
                ),
                NextTurnPayload(
                    message_text="好，那我晚点再说。",
                    strategy_used="self_follow_up",
                    state_after_turn=TurnStatePayload(
                        relationship_temperature="warm",
                        tension_level="low",
                        openness_level="medium",
                        initiative_balance="balanced",
                        defensiveness_level="low",
                        relationship_phase="warming",
                        active_sensitive_topics=[],
                        state_rationale="继续低压力推进。",
                    ),
                    generation_notes="我方顺着继续。",
                    should_stop=False,
                    stopping_reason=None,
                ),
            ]
        )
    )

    assert processed is True

    with session_scope() as session:
        job = session.query(SimulationJob).one()
        assert job.status == "completed"
        assert job.result_simulation_id is not None
        assert session.query(Simulation).count() == 1
        assert session.query(SimulationTurn).count() == 3
```

Add this API read test to `tests/test_simulations.py`:

```python
from if_then_mvp.worker import run_next_simulation_job


def test_get_simulation_returns_completed_job_result(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="ready",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=2,
        )
        session.add(batch)
        session.flush()

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="在吗",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="在的",
                    message_type="text",
                ),
            ]
        )
        session.flush()

        session.add(
            Segment(
                conversation_id=conversation.id,
                start_message_id=1,
                end_message_id=2,
                start_time="2025-03-02T20:18:03",
                end_time="2025-03-02T20:18:04",
                message_count=2,
                self_message_count=1,
                other_message_count=1,
                segment_kind="normal",
                source_message_ids=[1, 2],
            )
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=1,
                as_of_time="2025-03-02T20:18:03",
                relationship_temperature="warm",
                tension_level="low",
                openness_level="medium",
                initiative_balance="balanced",
                defensiveness_level="low",
                unresolved_conflict_flags=[],
                relationship_phase="warming",
                snapshot_summary="轻松的开场互动",
            )
        )
        session.add(
            SimulationJob(
                conversation_id=conversation.id,
                target_message_id=2,
                mode="single_reply",
                turn_count=1,
                replacement_content="如果你不忙，我们慢慢说也可以",
                status="queued",
                current_stage="queued",
                progress_percent=0,
                payload_json={"progress": {"current_stage_total_units": 2, "current_stage_completed_units": 0, "overall_total_units": 2, "overall_completed_units": 0, "status_message": "queued 0/2 steps"}},
            )
        )

    fake_llm = FakeSimulationLLM(
        [
            BranchAssessmentPayload(
                branch_direction="closer",
                state_shift_summary="新说法缓和了互动压力。",
                other_immediate_feeling="更放松",
                reply_strategy="light_follow_up",
                risk_flags=[],
                confidence=0.8,
            ),
            FirstReplyPayload(
                first_reply_text="好，那晚点聊也没事。",
                strategy_used="light_follow_up",
                first_reply_style_notes="先低压力接住。",
                state_after_turn=TurnStatePayload(**_state_payload()),
            ),
        ]
    )

    assert run_next_simulation_job(llm_client=fake_llm) is True

    with session_scope() as session:
        job = session.query(SimulationJob).one()
        result_simulation_id = job.result_simulation_id

    with TestClient(create_app()) as client:
        response = client.get(f"/simulations/{result_simulation_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["first_reply_text"] == "好，那晚点聊也没事。"
    assert body["simulated_turns"] == []
```

- [ ] **Step 2: Run the focused tests and verify they fail because the worker lane and fetch endpoint do not exist yet**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_worker.py::test_run_next_simulation_job_persists_final_result_and_links_job tests/test_simulations.py::test_get_simulation_returns_completed_job_result -q
```

Expected:
- FAIL
- Errors should show `run_next_simulation_job` or `GET /simulations/{id}` behavior is missing

- [ ] **Step 3: Implement the simulation worker lane, progress updates, and final `GET /simulations/{id}`**

Extend `src/if_then_mvp/simulation_jobs.py`:

```python
from sqlalchemy import select


def claim_next_simulation_job(session) -> SimulationJob | None:
    next_job = (
        session.execute(
            select(SimulationJob)
            .where(SimulationJob.status == "queued")
            .order_by(SimulationJob.id.asc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if next_job is None:
        return None
    next_job.status = "running"
    next_job.current_stage = "branch_assessment"
    next_job.started_at = utcnow()
    return next_job


def apply_simulation_job_progress(
    job: SimulationJob,
    *,
    current_stage: str,
    current_stage_completed_units: int,
    current_stage_total_units: int,
    overall_completed_units: int,
    overall_total_units: int,
    status_message: str,
    status: str | None = None,
    result_simulation_id: int | None = None,
    error_message: str | None = None,
) -> None:
    payload = dict(job.payload_json or {})
    payload["progress"] = {
        "current_stage_total_units": current_stage_total_units,
        "current_stage_completed_units": current_stage_completed_units,
        "overall_total_units": overall_total_units,
        "overall_completed_units": overall_completed_units,
        "status_message": status_message,
    }
    job.payload_json = payload
    job.current_stage = current_stage
    job.progress_percent = 0 if overall_total_units <= 0 else min(100, int((overall_completed_units * 100) / overall_total_units))
    if status is not None:
        job.status = status
    if result_simulation_id is not None:
        job.result_simulation_id = result_simulation_id
    job.error_message = error_message
    if status in {"completed", "failed", "cancelled"}:
        job.finished_at = utcnow()
```

Add this to `src/if_then_mvp/worker.py`:

```python
from if_then_mvp.models import Simulation, SimulationJob, SimulationTurn
from if_then_mvp.simulation import assess_branch, generate_first_reply, simulate_short_thread
from if_then_mvp.simulation_jobs import apply_simulation_job_progress, claim_next_simulation_job


def run_next_simulation_job(*, llm_client=None) -> bool:
    effective_llm = llm_client
    if effective_llm is None:
        try:
            effective_llm = _build_worker_runtime_llm_client()
        except RuntimeError:
            return False

    session = get_sessionmaker()()
    try:
        job = claim_next_simulation_job(session)
        if job is None:
            session.rollback()
            return False
        session.commit()
        job_id = job.id
    finally:
        session.close()

    session = get_sessionmaker()()
    try:
        job = session.get(SimulationJob, job_id)
        if job is None:
            return False

        total_units = 2 if job.mode == "single_reply" else job.turn_count + 1
        apply_simulation_job_progress(
            job,
            current_stage="branch_assessment",
            current_stage_completed_units=0,
            current_stage_total_units=1,
            overall_completed_units=0,
            overall_total_units=total_units,
            status_message="branch_assessment 0/1",
        )
        session.commit()

        context_pack = _build_simulation_context_pack(session, job=job)
        assessment = assess_branch(llm_client=effective_llm, context_pack=context_pack)
        apply_simulation_job_progress(
            job,
            current_stage="first_reply",
            current_stage_completed_units=1,
            current_stage_total_units=1,
            overall_completed_units=1,
            overall_total_units=total_units,
            status_message="first_reply 1/1",
        )
        session.commit()

        first_reply = generate_first_reply(llm_client=effective_llm, context_pack=context_pack, assessment=assessment)
        turns = (
            simulate_short_thread(
                llm_client=effective_llm,
                context_pack=context_pack,
                assessment=assessment,
                first_reply=first_reply,
                turn_count=job.turn_count,
            )
            if job.mode == "short_thread"
            else []
        )

        simulation = Simulation(
            conversation_id=job.conversation_id,
            target_message_id=job.target_message_id,
            mode=job.mode,
            replacement_content=job.replacement_content,
            context_pack_snapshot=context_pack,
            branch_assessment=assessment,
            first_reply_text=first_reply.first_reply_text,
            impact_summary=assessment["state_shift_summary"],
            status="completed",
        )
        session.add(simulation)
        session.flush()

        for turn in turns:
            session.add(SimulationTurn(simulation_id=simulation.id, **turn))
        session.flush()

        apply_simulation_job_progress(
            job,
            current_stage="completed",
            current_stage_completed_units=total_units,
            current_stage_total_units=total_units,
            overall_completed_units=total_units,
            overall_total_units=total_units,
            status_message=f"completed {total_units}/{total_units} steps",
            status="completed",
            result_simulation_id=simulation.id,
        )
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        failed_job = session.get(SimulationJob, job_id)
        if failed_job is not None:
            apply_simulation_job_progress(
                failed_job,
                current_stage="failed",
                current_stage_completed_units=0,
                current_stage_total_units=1,
                overall_completed_units=0,
                overall_total_units=1,
                status_message=f"failed {exc}",
                status="failed",
                error_message=str(exc),
            )
            session.commit()
        return True
    finally:
        session.close()
```

Update `run_forever()`:

```python
def run_forever(*, llm_client, poll_interval_seconds: int = 2) -> None:
    while True:
        processed_analysis = run_next_job(llm_client=llm_client, progress_reporter=ConsoleProgressReporter())
        processed_simulation = run_next_simulation_job(llm_client=llm_client)
        if not processed_analysis and not processed_simulation:
            time.sleep(poll_interval_seconds)
```

Add the final read endpoint to `src/if_then_mvp/api.py`:

```python
@app.get("/simulations/{simulation_id}", response_model=SimulationRead)
def get_simulation(simulation_id: int) -> SimulationRead:
    with session_scope() as session:
        simulation = session.get(Simulation, simulation_id)
        if simulation is None:
            raise HTTPException(status_code=404, detail="Simulation not found")

        turns = (
            session.execute(
                select(SimulationTurn)
                .where(SimulationTurn.simulation_id == simulation_id)
                .order_by(SimulationTurn.turn_index.asc(), SimulationTurn.id.asc())
            )
            .scalars()
            .all()
        )
        return SimulationRead(
            id=simulation.id,
            mode=simulation.mode,
            replacement_content=simulation.replacement_content,
            first_reply_text=simulation.first_reply_text,
            impact_summary=simulation.impact_summary,
            simulated_turns=[SimulationTurnRead.model_validate(item, from_attributes=True) for item in turns],
        )
```

- [ ] **Step 4: Run the focused worker/result tests again and verify they pass**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_worker.py::test_run_next_simulation_job_persists_final_result_and_links_job tests/test_simulations.py::test_get_simulation_returns_completed_job_result -q
```

Expected:
- PASS
- Both tests pass, proving the worker can complete a simulation job and the final result can be fetched separately

- [ ] **Step 5: Commit the worker-execution slice**

```powershell
git add src/if_then_mvp/api.py src/if_then_mvp/simulation_jobs.py src/if_then_mvp/worker.py tests/test_simulations.py tests/test_worker.py
git commit -m "Let the worker complete simulation jobs and persist final results" -m "Simulation execution now runs through a dedicated worker lane that updates job progress and only writes `simulations`/`simulation_turns` after a successful completion, keeping intermediate branch content out of the UI surface.

Constraint: Final branch text must remain hidden until the simulation job reaches completed
Rejected: Continue executing simulations inside the API request thread | prevents durable progress and recovery
Confidence: high
Scope-risk: broad
Directive: Keep simulation result persistence at the end of the worker flow; partial turns must not become user-visible records
Tested: python -m pytest tests/test_worker.py::test_run_next_simulation_job_persists_final_result_and_links_job tests/test_simulations.py::test_get_simulation_returns_completed_job_result -q
Not-tested: Cancellation semantics and desktop polling"
```

---

### Task 3: Soft-Cancel Superseded Simulation Jobs And Keep Latest-Wins Semantics

**Files:**
- Modify: `src/if_then_mvp/simulation_jobs.py`
- Modify: `src/if_then_mvp/api.py`
- Modify: `src/if_then_mvp/worker.py`
- Modify: `tests/test_simulations.py`
- Modify: `tests/test_worker.py`

- [ ] **Step 1: Write the failing cancellation tests for queued and running jobs**

Add this API-level test to `tests/test_simulations.py`:

```python
def _seed_minimal_simulation_conversation(tmp_path):
    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="ready",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=2,
        )
        session.add(batch)
        session.flush()

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="在吗",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="在的",
                    message_type="text",
                ),
            ]
        )
        session.flush()

        session.add(
            Segment(
                conversation_id=conversation.id,
                start_message_id=1,
                end_message_id=2,
                start_time="2025-03-02T20:18:03",
                end_time="2025-03-02T20:18:04",
                message_count=2,
                self_message_count=1,
                other_message_count=1,
                segment_kind="normal",
                source_message_ids=[1, 2],
            )
        )


def test_post_simulations_soft_cancels_previous_jobs_for_same_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    _seed_minimal_simulation_conversation(tmp_path)

    with TestClient(create_app()) as client:
        first = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 2,
                "replacement_content": "第一版改写",
                "mode": "single_reply",
                "turn_count": 1,
            },
        )
        second = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 2,
                "replacement_content": "第二版改写",
                "mode": "single_reply",
                "turn_count": 1,
            },
        )

    assert first.status_code == 202
    assert second.status_code == 202

    with session_scope() as session:
        jobs = session.query(SimulationJob).order_by(SimulationJob.id.asc()).all()
        assert jobs[0].status == "cancelled"
        assert jobs[1].status == "queued"
```

Add this worker-level test to `tests/test_worker.py`:

```python
def _seed_minimal_simulation_worker_fixture(tmp_path):
    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="ready",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=2,
        )
        session.add(batch)
        session.flush()

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="在吗",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="在的",
                    message_type="text",
                ),
            ]
        )
        session.flush()

        session.add(
            Segment(
                conversation_id=conversation.id,
                start_message_id=1,
                end_message_id=2,
                start_time="2025-03-02T20:18:03",
                end_time="2025-03-02T20:18:04",
                message_count=2,
                self_message_count=1,
                other_message_count=1,
                segment_kind="normal",
                source_message_ids=[1, 2],
            )
        )


def test_run_next_simulation_job_marks_cancel_requested_jobs_cancelled_without_persisting_results(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    _seed_minimal_simulation_worker_fixture(tmp_path)

    with session_scope() as session:
        job = SimulationJob(
            conversation_id=1,
            target_message_id=2,
            mode="single_reply",
            turn_count=1,
            replacement_content="如果你不忙，我们慢慢说也可以",
            status="running",
            current_stage="branch_assessment",
            progress_percent=0,
            payload_json={"progress": {"current_stage_total_units": 2, "current_stage_completed_units": 0, "overall_total_units": 2, "overall_completed_units": 0, "status_message": "branch_assessment 0/1"}},
            cancel_requested_at=datetime.now(timezone.utc),
        )
        session.add(job)

    processed = run_next_simulation_job(llm_client=FakeSimulationLLM([]))

    assert processed is True

    with session_scope() as session:
        job = session.query(SimulationJob).one()
        assert job.status == "cancelled"
        assert session.query(Simulation).count() == 0
        assert session.query(SimulationTurn).count() == 0
```

- [ ] **Step 2: Run the cancellation tests and verify they fail**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_simulations.py::test_post_simulations_soft_cancels_previous_jobs_for_same_conversation tests/test_worker.py::test_run_next_simulation_job_marks_cancel_requested_jobs_cancelled_without_persisting_results -q
```

Expected:
- FAIL
- One failure should show the old queued job was not cancelled
- One failure should show running jobs ignore `cancel_requested_at`

- [ ] **Step 3: Implement soft cancellation for queued and running simulation jobs**

In `src/if_then_mvp/simulation_jobs.py`, add:

```python
def cancel_superseded_simulation_jobs(session, *, conversation_id: int) -> None:
    rows = (
        session.execute(
            select(SimulationJob)
            .where(
                SimulationJob.conversation_id == conversation_id,
                SimulationJob.status.in_(("queued", "running")),
            )
            .order_by(SimulationJob.id.asc())
        )
        .scalars()
        .all()
    )
    for job in rows:
        if job.status == "queued":
            apply_simulation_job_progress(
                job,
                current_stage="cancelled",
                current_stage_completed_units=0,
                current_stage_total_units=1,
                overall_completed_units=0,
                overall_total_units=max(1, int(((job.payload_json or {}).get("progress", {}).get("overall_total_units", 1) or 1)),
                status_message="cancelled before execution",
                status="cancelled",
            )
        else:
            job.cancel_requested_at = utcnow()
```

Call it from `POST /simulations` in `src/if_then_mvp/api.py` before creating the new job:

```python
from if_then_mvp.simulation_jobs import cancel_superseded_simulation_jobs

cancel_superseded_simulation_jobs(session, conversation_id=payload.conversation_id)
```

Add a helper and early-exit checks in `src/if_then_mvp/worker.py`:

```python
def _simulation_job_cancel_requested(job: SimulationJob) -> bool:
    return job.cancel_requested_at is not None


def _mark_simulation_job_cancelled(job: SimulationJob, *, status_message: str) -> None:
    progress = (job.payload_json or {}).get("progress", {})
    total_units = int(progress.get("overall_total_units", 1) or 1)
    completed_units = int(progress.get("overall_completed_units", 0) or 0)
    apply_simulation_job_progress(
        job,
        current_stage="cancelled",
        current_stage_completed_units=completed_units,
        current_stage_total_units=total_units,
        overall_completed_units=completed_units,
        overall_total_units=total_units,
        status_message=status_message,
        status="cancelled",
    )
```

Use the helper inside `run_next_simulation_job()` before each LLM call and before final result persistence:

```python
session.refresh(job)
if _simulation_job_cancel_requested(job):
    _mark_simulation_job_cancelled(job, status_message="cancelled before branch_assessment")
    session.commit()
    return True
```

- [ ] **Step 4: Run the cancellation tests again and verify they pass**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_simulations.py::test_post_simulations_soft_cancels_previous_jobs_for_same_conversation tests/test_worker.py::test_run_next_simulation_job_marks_cancel_requested_jobs_cancelled_without_persisting_results -q
```

Expected:
- PASS
- Both tests pass, proving queued jobs cancel immediately and running jobs honor `cancel_requested_at`

- [ ] **Step 5: Commit the cancellation slice**

```powershell
git add src/if_then_mvp/api.py src/if_then_mvp/simulation_jobs.py src/if_then_mvp/worker.py tests/test_simulations.py tests/test_worker.py
git commit -m "Cancel superseded simulation jobs when newer rewrites arrive" -m "Posting a new simulation for the same conversation now cancels queued work immediately and flags running work for cooperative cancellation, so the desktop client can follow only the newest rewrite attempt.

Constraint: Cancellation is soft; active LLM calls may finish in the background but their results must be discarded
Rejected: Hard-stop the in-flight LLM request | unavailable in the current synchronous client stack
Confidence: high
Scope-risk: moderate
Directive: Newer simulation requests always win per conversation; do not resurrect cancelled jobs in the UI
Tested: python -m pytest tests/test_simulations.py::test_post_simulations_soft_cancels_previous_jobs_for_same_conversation tests/test_worker.py::test_run_next_simulation_job_marks_cancel_requested_jobs_cancelled_without_persisting_results -q
Not-tested: Desktop polling behavior"
```

---

### Task 4: Teach The Desktop Client The New Simulation Job Types, Services, And Progress Labels

**Files:**
- Create: `desktop/src/lib/simulationJobProgress.ts`
- Create: `desktop/tests/simulationJobProgress.test.ts`
- Modify: `desktop/src/types/api.ts`
- Modify: `desktop/src/lib/services/simulationService.ts`
- Modify: `desktop/src/lib/chatState.ts`

- [ ] **Step 1: Write the failing frontend helper tests for simulation job progress labels**

Create `desktop/tests/simulationJobProgress.test.ts`:

```ts
import { describe, expect, it } from 'vitest'

import { resolveSimulationJobProgress } from '../src/lib/simulationJobProgress'
import type { SimulationJobRead } from '../src/types/api'

function buildJob(overrides: Partial<SimulationJobRead>): SimulationJobRead {
  return {
    id: 31,
    conversation_id: 7,
    target_message_id: 12,
    mode: 'short_thread',
    turn_count: 4,
    replacement_content: '如果你不忙，我们慢慢说也可以',
    status: 'running',
    current_stage: 'branch_assessment',
    progress_percent: 25,
    current_stage_percent: 100,
    current_stage_total_units: 1,
    current_stage_completed_units: 1,
    overall_total_units: 4,
    overall_completed_units: 1,
    status_message: 'branch_assessment 1/1',
    result_simulation_id: null,
    error_message: null,
    ...overrides,
  }
}

describe('resolveSimulationJobProgress', () => {
  it('maps branch assessment to a running progress bar', () => {
    expect(resolveSimulationJobProgress(buildJob({ current_stage: 'branch_assessment', progress_percent: 25 }))).toEqual({
      label: '分支判断 25%',
      percent: 25,
      tone: 'running',
    })
  })

  it('maps short-thread turn generation using the current round label', () => {
    expect(
      resolveSimulationJobProgress(
        buildJob({
          current_stage: 'turn_generation',
          progress_percent: 75,
          status_message: 'turn_generation turn 3/4',
        }),
      ),
    ).toEqual({
      label: '第 3 轮 75%',
      percent: 75,
      tone: 'running',
    })
  })

  it('maps failed jobs into a red progress bar', () => {
    expect(resolveSimulationJobProgress(buildJob({ status: 'failed', current_stage: 'failed', progress_percent: 50 }))).toEqual({
      label: '推演失败',
      percent: 100,
      tone: 'failed',
    })
  })
})
```

- [ ] **Step 2: Run the helper test to verify it fails because the job type and progress mapper do not exist yet**

Run:

```powershell
cd D:\newProj\desktop
npm test -- simulationJobProgress.test.ts
```

Expected:
- FAIL
- The error should show `SimulationJobRead` and `resolveSimulationJobProgress` are missing

- [ ] **Step 3: Add the new desktop API types, services, and progress helper**

In `desktop/src/types/api.ts`, add:

```ts
export type SimulationJobRead = {
  id: number
  conversation_id: number
  target_message_id: number
  mode: 'single_reply' | 'short_thread'
  turn_count: number
  replacement_content: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  current_stage: 'queued' | 'branch_assessment' | 'first_reply' | 'turn_generation' | 'completed' | 'failed' | 'cancelled'
  progress_percent: number
  current_stage_percent: number
  current_stage_total_units: number
  current_stage_completed_units: number
  overall_total_units: number
  overall_completed_units: number
  status_message: string | null
  result_simulation_id: number | null
  error_message: string | null
}
```

Replace `desktop/src/lib/services/simulationService.ts` with:

```ts
import { apiClient } from '../apiClient'
import type { SimulationCreate, SimulationJobRead, SimulationRead } from '../../types/api'

export function createSimulation(payload: SimulationCreate): Promise<SimulationJobRead> {
  return apiClient.post<SimulationJobRead>('/simulations', payload)
}

export function readSimulationJob(jobId: number): Promise<SimulationJobRead> {
  return apiClient.get<SimulationJobRead>(`/simulation-jobs/${jobId}`)
}

export function listConversationSimulationJobs(conversationId: number, limit?: number): Promise<SimulationJobRead[]> {
  const query = limit === undefined ? '' : `?limit=${limit}`
  return apiClient.get<SimulationJobRead[]>(`/conversations/${conversationId}/simulation-jobs${query}`)
}

export function readSimulation(simulationId: number): Promise<SimulationRead> {
  return apiClient.get<SimulationRead>(`/simulations/${simulationId}`)
}
```

Create `desktop/src/lib/simulationJobProgress.ts`:

```ts
import type { FrontAnalysisProgress } from '../frontui/types'
import type { SimulationJobRead } from '../types/api'

function resolveStageLabel(job: SimulationJobRead): string {
  if (job.status === 'completed') return '推演完成'
  if (job.status === 'failed') return '推演失败'
  if (job.status === 'cancelled') return '已取消'

  switch (job.current_stage) {
    case 'queued':
      return '等待启动'
    case 'branch_assessment':
      return '分支判断'
    case 'first_reply':
      return '首轮回复'
    case 'turn_generation': {
      const match = job.status_message?.match(/turn_generation turn (\d+)\/(\d+)/)
      return match ? `第 ${match[1]} 轮` : '多轮推演'
    }
    default:
      return '推演中'
  }
}

export function resolveSimulationJobProgress(job: SimulationJobRead | null | undefined): FrontAnalysisProgress | null {
  if (!job) return null
  if (job.status === 'completed') return null
  if (job.status === 'failed') return { label: '推演失败', percent: 100, tone: 'failed' }
  if (job.status === 'cancelled') return null

  const percent = Number.isFinite(job.progress_percent) ? Math.max(0, Math.min(100, Math.round(job.progress_percent))) : 0
  return {
    label: `${resolveStageLabel(job)} ${percent}%`,
    percent,
    tone: 'running',
  }
}
```

Extend `desktop/src/lib/chatState.ts`:

```ts
export type SimulationJobRequestSnapshot = {
  requestId: number
  conversationId: number
  jobId: number
}

export function isSimulationJobRequestCurrent(input: {
  activeRequest: SimulationJobRequestSnapshot | null
  requestId: number
  conversationId: number | null
  jobId: number | null
}): boolean {
  return (
    input.activeRequest !== null &&
    input.activeRequest.requestId === input.requestId &&
    input.activeRequest.conversationId === input.conversationId &&
    input.activeRequest.jobId === input.jobId
  )
}
```

- [ ] **Step 4: Run the helper test again and verify it passes**

Run:

```powershell
cd D:\newProj\desktop
npm test -- simulationJobProgress.test.ts
```

Expected:
- PASS
- `3 tests` pass

- [ ] **Step 5: Commit the desktop type/service/progress slice**

```powershell
git add desktop/src/types/api.ts desktop/src/lib/services/simulationService.ts desktop/src/lib/chatState.ts desktop/src/lib/simulationJobProgress.ts desktop/tests/simulationJobProgress.test.ts
git commit -m "Teach the desktop client to read simulation job progress" -m "The renderer now knows about simulation jobs, can call the new queue/list/read endpoints, and can map real simulation stages into progress-bar labels without assuming intermediate branch content is available.

Constraint: Desktop must consume only job metadata until the final simulation result is ready
Rejected: Reuse analysisProgress for simulation jobs | simulation stages and completion semantics differ
Confidence: high
Scope-risk: narrow
Directive: Keep simulation job progress mapping separate from analysis job progress mapping
Tested: cd desktop && npm test -- simulationJobProgress.test.ts
Not-tested: Full App integration or recovery behavior"
```

---

### Task 5: Poll The Latest Simulation Job Before Rendering Branch Results

**Files:**
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/tests/visualShell.test.tsx`

- [ ] **Step 1: Rewrite the visual-shell tests to model async jobs, latest-wins polling, and result recovery**

In `desktop/tests/visualShell.test.tsx`, replace the synchronous simulation mock shape:

```ts
import {
  createSimulation,
  listConversationSimulationJobs,
  readSimulation,
  readSimulationJob,
} from '../src/lib/services/simulationService'
```

Update the simulation service mock:

```ts
vi.mock('../src/lib/services/simulationService', () => ({
  createSimulation: vi.fn(),
  readSimulationJob: vi.fn(),
  listConversationSimulationJobs: vi.fn(),
  readSimulation: vi.fn(),
}))
```

Add these tests:

```ts
it('submits a simulation job, polls its progress, and only renders the branch result after completion', async () => {
  const deferredCreate = createDeferred<Awaited<ReturnType<typeof createSimulation>>>()
  const deferredJob = createDeferred<Awaited<ReturnType<typeof readSimulationJob>>>()

  mockedCreateSimulation.mockReturnValueOnce(deferredCreate.promise)
  mockedReadSimulationJob.mockReturnValueOnce(deferredJob.promise)
  mockedReadSimulation.mockResolvedValueOnce({
    id: 88,
    mode: 'short_thread',
    replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
    first_reply_text: '好，那你先休息。',
    impact_summary: '冲突被降温。',
    simulated_turns: [
      {
        turn_index: 1,
        speaker_role: 'other',
        message_text: '好，那你先休息。',
        strategy_used: 'de-escalate',
        state_after_turn: {},
        generation_notes: null,
      },
    ],
  })

  await act(async () => {
    deferredCreate.resolve({
      id: 31,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'short_thread',
      turn_count: 3,
      replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
      status: 'queued',
      current_stage: 'queued',
      progress_percent: 0,
      current_stage_percent: 0,
      current_stage_total_units: 1,
      current_stage_completed_units: 0,
      overall_total_units: 4,
      overall_completed_units: 0,
      status_message: 'queued 0/4 steps',
      result_simulation_id: null,
      error_message: null,
    })
  })
  await flushAsyncWork(6)

  expect(container.textContent).toContain('等待启动')
  expect(container.textContent).not.toContain('好，那你先休息。')

  await act(async () => {
    deferredJob.resolve({
      id: 31,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'short_thread',
      turn_count: 3,
      replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 4,
      current_stage_completed_units: 4,
      overall_total_units: 4,
      overall_completed_units: 4,
      status_message: 'completed 4/4 steps',
      result_simulation_id: 88,
      error_message: null,
    })
  })
  await flushAsyncWork(8)

  expect(mockedReadSimulation).toHaveBeenCalledWith(88)
  expect(container.textContent).toContain('好，那你先休息。')
})

it('ignores an older simulation job when a newer rewrite request takes over', async () => {
  mockedCreateSimulation
    .mockResolvedValueOnce({
      id: 31,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'single_reply',
      turn_count: 1,
      replacement_content: '第一版改写',
      status: 'queued',
      current_stage: 'queued',
      progress_percent: 0,
      current_stage_percent: 0,
      current_stage_total_units: 1,
      current_stage_completed_units: 0,
      overall_total_units: 2,
      overall_completed_units: 0,
      status_message: 'queued 0/2 steps',
      result_simulation_id: null,
      error_message: null,
    })
    .mockResolvedValueOnce({
      id: 32,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'single_reply',
      turn_count: 1,
      replacement_content: '第二版改写',
      status: 'queued',
      current_stage: 'queued',
      progress_percent: 0,
      current_stage_percent: 0,
      current_stage_total_units: 1,
      current_stage_completed_units: 0,
      overall_total_units: 2,
      overall_completed_units: 0,
      status_message: 'queued 0/2 steps',
      result_simulation_id: null,
      error_message: null,
    })
  mockedReadSimulationJob
    .mockResolvedValueOnce({
      id: 31,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'single_reply',
      turn_count: 1,
      replacement_content: '第一版改写',
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 2,
      current_stage_completed_units: 2,
      overall_total_units: 2,
      overall_completed_units: 2,
      status_message: 'completed 2/2 steps',
      result_simulation_id: 90,
      error_message: null,
    })
    .mockResolvedValueOnce({
      id: 32,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'single_reply',
      turn_count: 1,
      replacement_content: '第二版改写',
      status: 'running',
      current_stage: 'first_reply',
      progress_percent: 50,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 2,
      overall_completed_units: 1,
      status_message: 'first_reply 1/1',
      result_simulation_id: null,
      error_message: null,
    })

  mockedReadSimulation.mockResolvedValueOnce({
    id: 90,
    mode: 'single_reply',
    replacement_content: '第一版改写',
    first_reply_text: '旧结果不应覆盖',
    impact_summary: '旧结果',
    simulated_turns: [],
  })

  const { root, container } = setupDom()

  await act(async () => {
    root.render(<App />)
  })
  await flushAsyncWork(10)

  const rewriteTarget = container.querySelector('[data-chat-message-id="message-12"] .cursor-pointer')
  await act(async () => {
    if (rewriteTarget) {
      getReactProps<{ onDoubleClick?: () => void }>(rewriteTarget).onDoubleClick?.()
    }
  })
  await flushAsyncWork(4)

  const rewriteEditor = container.querySelector('textarea')
  await act(async () => {
    if (rewriteEditor) {
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(rewriteEditor).onChange?.({
        target: { value: '第一版改写' },
      })
    }
  })
  await flushAsyncWork(2)

  await act(async () => {
    if (rewriteEditor) {
      getReactProps<{ onKeyDown?: (event: { key: string; shiftKey: boolean; preventDefault: () => void }) => void }>(rewriteEditor).onKeyDown?.({
        key: 'Enter',
        shiftKey: false,
        preventDefault: () => undefined,
      })
    }
  })
  await flushAsyncWork(6)

  await act(async () => {
    if (rewriteEditor) {
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(rewriteEditor).onChange?.({
        target: { value: '第二版改写' },
      })
    }
  })
  await flushAsyncWork(2)

  await act(async () => {
    if (rewriteEditor) {
      getReactProps<{ onKeyDown?: (event: { key: string; shiftKey: boolean; preventDefault: () => void }) => void }>(rewriteEditor).onKeyDown?.({
        key: 'Enter',
        shiftKey: false,
        preventDefault: () => undefined,
      })
    }
  })
  await flushAsyncWork(8)

  expect(container.textContent).toContain('第二版改写')
  expect(container.textContent).not.toContain('旧结果不应覆盖')
})

it('restores the latest running simulation job when the conversation loads', async () => {
  mockedListConversationSimulationJobs.mockResolvedValueOnce([
    {
      id: 31,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'single_reply',
      turn_count: 1,
      replacement_content: '如果你现在忙，晚点聊也可以',
      status: 'running',
      current_stage: 'first_reply',
      progress_percent: 50,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 2,
      overall_completed_units: 1,
      status_message: 'first_reply 1/1',
      result_simulation_id: null,
      error_message: null,
    },
  ])

  mockedReadSimulationJob.mockResolvedValueOnce({
    id: 31,
    conversation_id: 7,
    target_message_id: 12,
    mode: 'single_reply',
    turn_count: 1,
    replacement_content: '如果你现在忙，晚点聊也可以',
    status: 'running',
    current_stage: 'first_reply',
    progress_percent: 50,
    current_stage_percent: 100,
    current_stage_total_units: 1,
    current_stage_completed_units: 1,
    overall_total_units: 2,
    overall_completed_units: 1,
    status_message: 'first_reply 1/1',
    result_simulation_id: null,
    error_message: null,
  })

  const { root, container } = setupDom()

  await act(async () => {
    root.render(<App />)
  })
  await flushAsyncWork(10)

  expect(mockedListConversationSimulationJobs).toHaveBeenCalledWith(7, 1)
  expect(mockedReadSimulationJob).toHaveBeenCalledWith(31)
  expect(container.textContent).toContain('首轮回复 50%')
})
```

- [ ] **Step 2: Run the focused visual-shell suite and verify it fails**

Run:

```powershell
cd D:\newProj\desktop
npm test -- visualShell.test.tsx
```

Expected:
- FAIL
- Failures should show that `App.tsx` still assumes `createSimulation()` directly returns `SimulationRead`

- [ ] **Step 3: Implement the new App polling/recovery/latest-wins state machine**

In `desktop/src/App.tsx`, update the imports:

```ts
import {
  createSimulation,
  listConversationSimulationJobs,
  readSimulation,
  readSimulationJob,
} from './lib/services/simulationService'
import { resolveSimulationJobProgress } from './lib/simulationJobProgress'
import { isSimulationJobRequestCurrent, type SimulationJobRequestSnapshot } from './lib/chatState'
import type { SimulationJobRead } from './types/api'
```

Extend `RewriteDraft`:

```ts
type RewriteDraft = {
  conversationId: number
  targetMessageId: number
  originalMessage: string
  targetMessageTimestamp: string
  replacementContent: string
  status: 'editing' | 'pending' | 'completed'
  simulation: SimulationRead | null
  simulationJob: SimulationJobRead | null
  errorMessage: string | null
  pendingStageLabel: string | null
}
```

Add the new refs/state near the top of `App()`:

```ts
const [simulationJobsByConversation, setSimulationJobsByConversation] = useState<Record<number, SimulationJobRead | null>>({})
const activeSimulationJobRequestRef = useRef<SimulationJobRequestSnapshot | null>(null)
```

When opening rewrite mode, initialize `simulationJob: null`:

```ts
setRewriteDraft({
  conversationId: selectedConversationId,
  targetMessageId: targetMessage.id,
  originalMessage: targetMessage.content_text,
  targetMessageTimestamp: targetMessage.timestamp,
  replacementContent: targetMessage.content_text,
  status: 'editing',
  simulation: null,
  simulationJob: null,
  errorMessage: null,
  pendingStageLabel: null,
})
```

Rewrite `handleSubmitRewrite()`:

```ts
const simulationJob = await createSimulation({
  conversation_id: selectedConversationId,
  target_message_id: rewriteDraft.targetMessageId,
  replacement_content: trimmedReplacementContent,
  mode: settingsFormState.simulationMode,
  turn_count: settingsFormState.simulationTurnCount,
})

activeSimulationJobRequestRef.current = {
  requestId,
  conversationId: selectedConversationId,
  jobId: simulationJob.id,
}

setSimulationJobsByConversation((current) => ({
  ...current,
  [selectedConversationId]: simulationJob,
}))
setRewriteDraft((current) =>
  current
    ? {
        ...current,
        replacementContent: trimmedReplacementContent,
        status: 'pending',
        simulation: null,
        simulationJob,
        errorMessage: null,
        pendingStageLabel: null,
      }
    : current,
)
```

Add a polling effect:

```ts
useEffect(() => {
  if (
    state.phase !== 'ready' ||
    !rewriteDraft ||
    rewriteDraft.status !== 'pending' ||
    !rewriteDraft.simulationJob ||
    selectedConversationId === null
  ) {
    return
  }

  let cancelled = false
  let timeoutId: number | null = null
  const requestSnapshot = activeSimulationJobRequestRef.current

  const poll = async () => {
    const nextJob = await readSimulationJob(rewriteDraft.simulationJob!.id)
    if (
      cancelled ||
      !isSimulationJobRequestCurrent({
        activeRequest: activeSimulationJobRequestRef.current,
        requestId: requestSnapshot?.requestId ?? -1,
        conversationId: selectedConversationIdRef.current,
        jobId: rewriteDraftRef.current?.simulationJob?.id ?? null,
      })
    ) {
      return
    }

    setSimulationJobsByConversation((current) => ({
      ...current,
      [selectedConversationId]: nextJob,
    }))
    setRewriteDraft((current) => (current ? { ...current, simulationJob: nextJob } : current))

    if (nextJob.status === 'completed' && nextJob.result_simulation_id !== null) {
      const simulation = await readSimulation(nextJob.result_simulation_id)
      if (cancelled) return
      setChatViewState({ mode: 'history' })
      setRewriteDraft((current) =>
        current
          ? {
              ...current,
              status: 'completed',
              simulationJob: nextJob,
              simulation,
              errorMessage: null,
            }
          : current,
      )
      activeSimulationJobRequestRef.current = null
      return
    }

    if (nextJob.status === 'failed' || nextJob.status === 'cancelled') {
      setRewriteDraft((current) =>
        current
          ? {
              ...current,
              status: 'editing',
              simulationJob: nextJob,
              simulation: null,
              errorMessage: nextJob.status === 'failed' ? (nextJob.error_message ?? '推演失败') : '已被新的推演请求替代',
            }
          : current,
      )
      return
    }

    timeoutId = window.setTimeout(() => {
      void poll()
    }, 1500)
  }

  timeoutId = window.setTimeout(() => {
    void poll()
  }, 1500)

  return () => {
    cancelled = true
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId)
    }
  }
}, [rewriteDraft?.status, rewriteDraft?.simulationJob?.id, selectedConversationId, state.phase])
```

On conversation hydrate, restore the latest job:

```ts
useEffect(() => {
  if (state.phase !== 'ready' || selectedConversationId === null) {
    return
  }

  let cancelled = false

  const restoreLatestSimulationJob = async () => {
    const jobs = await listConversationSimulationJobs(selectedConversationId, 1)
    if (cancelled || jobs.length === 0) {
      return
    }

    const latestJob = jobs[0]
    setSimulationJobsByConversation((current) => ({
      ...current,
      [selectedConversationId]: latestJob,
    }))

    if (latestJob.status === 'completed' && latestJob.result_simulation_id !== null) {
      const simulation = await readSimulation(latestJob.result_simulation_id)
      if (cancelled) return
      setRewriteDraft({
        conversationId: selectedConversationId,
        targetMessageId: latestJob.target_message_id,
        originalMessage: '',
        targetMessageTimestamp: '',
        replacementContent: latestJob.replacement_content,
        status: 'completed',
        simulationJob: latestJob,
        simulation,
        errorMessage: null,
        pendingStageLabel: null,
      })
      return
    }

    if (latestJob.status === 'queued' || latestJob.status === 'running') {
      setRewriteDraft((current) =>
        current && current.conversationId === selectedConversationId
          ? { ...current, status: 'pending', simulationJob: latestJob }
          : current
      )
    }
  }

  void restoreLatestSimulationJob()
  return () => {
    cancelled = true
  }
}, [selectedConversationId, state.phase])
```

Finally, feed the real polled job progress into the overlay:

```ts
const selectedSimulationJob = selectedConversationId === null ? null : simulationJobsByConversation[selectedConversationId] ?? null
const selectedSimulationProgress = useMemo(
  () => resolveSimulationJobProgress(rewriteDraft?.simulationJob ?? selectedSimulationJob),
  [rewriteDraft?.simulationJob, selectedSimulationJob],
)
```

And wire `rewriteState.stageLabel` from the live job instead of a local placeholder:

```ts
stageLabel:
  rewriteDraft.status === 'pending'
    ? selectedSimulationProgress?.label ?? '等待启动'
    : null,
```

- [ ] **Step 4: Run the focused visual-shell suite again and verify it passes**

Run:

```powershell
cd D:\newProj\desktop
npm test -- visualShell.test.tsx
```

Expected:
- PASS
- The simulation-related visual tests pass with the new async job flow

- [ ] **Step 5: Commit the App integration slice**

```powershell
git add desktop/src/App.tsx desktop/tests/visualShell.test.tsx
git commit -m "Poll the latest simulation job before rendering branch results" -m "The desktop rewrite flow now submits simulation jobs, polls only the newest job per conversation, restores the latest job on reload, and fetches final branch content only after the backend marks the job completed.

Constraint: The UI must never show partial branch content while a simulation job is still running
Rejected: Keep awaiting createSimulation() for a final SimulationRead | incompatible with real progress and recovery
Confidence: medium
Scope-risk: broad
Directive: Guard every polled simulation update with the latest request token so older jobs cannot overwrite newer rewrite attempts
Tested: cd desktop && npm test -- visualShell.test.tsx
Not-tested: Full desktop suite, typecheck, or backend integration"
```

---

### Task 6: Run Full Regression And Prepare The Branch For Execution Handoff

**Files:**
- Verify: `tests/test_simulations.py`
- Verify: `tests/test_worker.py`
- Verify: `desktop/tests/visualShell.test.tsx`
- Verify: `desktop/tests/simulationJobProgress.test.ts`
- Verify: `desktop/src/**`

- [ ] **Step 1: Run the focused backend simulation suite**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_simulations.py tests/test_worker.py -q
```

Expected:
- PASS
- All simulation API + worker tests pass

- [ ] **Step 2: Run the full backend pytest suite**

Run:

```powershell
cd D:\newProj
python -m pytest -q
```

Expected:
- PASS
- Full backend suite is green

- [ ] **Step 3: Run the full desktop verification suite**

Run:

```powershell
cd D:\newProj\desktop
npm test
npm run typecheck
```

Expected:
- PASS
- All desktop tests pass
- TypeScript typecheck passes

- [ ] **Step 4: Inspect the final diff and make sure only simulation job progress work is included**

Run:

```powershell
cd D:\newProj
git status --short
git diff --stat
```

Expected:
- Only backend simulation job, worker, desktop simulation polling, and test files are changed
- No unrelated Electron or analysis-job regressions are bundled in

- [ ] **Step 5: Commit the final integration verification or the last required fix**

If verification exposed no additional code changes, do not manufacture a no-op commit.

If verification required a final fix, use:

```powershell
git add src/if_then_mvp/api.py src/if_then_mvp/simulation_jobs.py src/if_then_mvp/worker.py tests/test_simulations.py tests/test_worker.py desktop/src/types/api.ts desktop/src/lib/services/simulationService.ts desktop/src/lib/chatState.ts desktop/src/lib/simulationJobProgress.ts desktop/src/App.tsx desktop/tests/simulationJobProgress.test.ts desktop/tests/visualShell.test.tsx
git commit -m "Finish the simulation job progress integration" -m "The backend and desktop client now agree on the asynchronous simulation job contract, including durable progress, cooperative cancellation, latest-wins polling, and deferred final-result rendering.

Constraint: Recovery after reload must use persisted simulation job state rather than optimistic local UI state
Rejected: Surface partial branch text while polling | violates the approved product contract
Confidence: medium
Scope-risk: broad
Directive: Keep final simulation rendering strictly downstream of a completed simulation job with a non-null result_simulation_id
Tested: python -m pytest tests/test_simulations.py tests/test_worker.py -q; python -m pytest -q; cd desktop && npm test; cd desktop && npm run typecheck
Not-tested: Manual Electron GUI validation"
```

---

## Self-Review Checklist

- Spec coverage:
  - `simulation_jobs` 独立实体有专门任务
  - `/simulations` 改为异步 job 返回有专门任务
  - worker 真实阶段进度、最终结果落库、软取消都有专门任务
  - 前端轮询、latest-wins、恢复逻辑都有专门任务
  - 前端不暴露中间结果由 worker + App 状态机共同保证
- Placeholder scan:
  - 无 TBD / TODO / “类似上一步”
  - 所有步骤都给了实际文件、代码片段、命令和预期
- Type consistency:
  - 后端统一使用 `SimulationJobRead`
  - 前端统一使用 `createSimulation -> SimulationJobRead -> readSimulationJob -> readSimulation`
  - 结果关联字段统一为 `result_simulation_id`
