from pathlib import Path

from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import (
    AnalysisJob,
    AppSetting,
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    Simulation,
    SimulationJob,
    SimulationTurn,
    Topic,
    TopicLink,
)
from if_then_mvp.worker import ConsoleProgressReporter, ProgressSnapshot, _claim_next_job, run_next_job
from if_then_mvp.worker import run_next_simulation_job
from if_then_mvp.simulation import BranchAssessmentPayload, FirstReplyPayload, NextTurnPayload, TurnStatePayload


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


class ExplodingLLM:
    def chat_json(self, *, system_prompt, user_prompt, response_model):
        raise RuntimeError("boom")


class SlowSummaryLLM:
    def __init__(self, advance_time: callable) -> None:
        self.advance_time = advance_time

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        if response_model.__name__ == "SegmentSummaryPayload":
            self.advance_time(31.0)
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


class TimedLLM(FakeLLM):
    def __init__(self, advance_time: callable) -> None:
        self.advance_time = advance_time

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        self.advance_time(
            {
                "SegmentSummaryPayload": 2.0,
                "TopicAssignmentPayload": 3.0,
                "TopicCreationPayload": 5.0,
                "TopicMergeReviewPayload": 7.0,
                "PersonaPayload": 11.0,
                "SnapshotPayload": 13.0,
            }.get(response_model.__name__, 1.0)
        )
        return super().chat_json(system_prompt=system_prompt, user_prompt=user_prompt, response_model=response_model)


class MultiTopicLLM:
    def __init__(self) -> None:
        self.summary_index = 0
        self.assignment_index = 0
        self.creation_index = 0

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        if response_model.__name__ == "SegmentSummaryPayload":
            payloads = [
                {
                    "summary_text": "双方围绕宿舍办理流程和 timing 卡点继续吐槽。",
                    "main_topics": ["宿舍办理", "timing 卡点"],
                    "self_stance": "顺着话题继续吐槽",
                    "other_stance": "先发起宿舍相关讨论",
                    "emotional_tone": "轻松",
                    "interaction_pattern": "轻松调侃",
                    "has_conflict": False,
                    "has_repair": False,
                    "has_closeness_signal": False,
                    "outcome": "继续讨论宿舍问题",
                    "relationship_impact": "neutral_positive",
                    "confidence": 0.84,
                },
                {
                    "summary_text": "双方聊到最近天气忽冷忽热，顺着聊穿衣和体感。",
                    "main_topics": ["天气变化", "冷热感受"],
                    "self_stance": "接住天气话题",
                    "other_stance": "先提到天气变化",
                    "emotional_tone": "轻松",
                    "interaction_pattern": "日常接话",
                    "has_conflict": False,
                    "has_repair": False,
                    "has_closeness_signal": False,
                    "outcome": "继续轻松聊天",
                    "relationship_impact": "neutral_positive",
                    "confidence": 0.82,
                },
                {
                    "summary_text": "双方一边继续聊宿舍办理，一边顺带吐槽天气太热。",
                    "main_topics": ["宿舍办理", "天气变化"],
                    "self_stance": "同时延续两个话题",
                    "other_stance": "接住宿舍和天气两条线",
                    "emotional_tone": "轻松",
                    "interaction_pattern": "多线轻松接话",
                    "has_conflict": False,
                    "has_repair": False,
                    "has_closeness_signal": False,
                    "outcome": "两条话题都继续展开",
                    "relationship_impact": "neutral_positive",
                    "confidence": 0.8,
                },
            ]
            payload = payloads[self.summary_index]
            self.summary_index += 1
            return response_model(**payload)

        if response_model.__name__ == "TopicAssignmentPayload":
            payloads = [
                {"matched_topics": [], "should_create_new_topic": True},
                {"matched_topics": [], "should_create_new_topic": True},
                {
                    "matched_topics": [
                        {"topic_id": 1, "link_reason": "当前片段继续讨论宿舍/住宿话题。", "score": 0.93},
                        {"topic_id": 2, "link_reason": "当前片段也明确触及天气相关话题。", "score": 0.87},
                    ],
                    "should_create_new_topic": False,
                },
            ]
            payload = payloads[self.assignment_index]
            self.assignment_index += 1
            return response_model(**payload)

        if response_model.__name__ == "TopicCreationPayload":
            payloads = [
                {
                    "topic_name": "宿舍/住宿讨论",
                    "topic_summary": "围绕宿舍、住宿安排、办理流程与相关问题的持续讨论。",
                    "topic_status": "ongoing",
                    "relevance_reason": "当前片段明确围绕宿舍办理与住宿问题展开。",
                },
                {
                    "topic_name": "天气相关话题",
                    "topic_summary": "围绕天气变化、冷热感受和天气状况展开的持续讨论。",
                    "topic_status": "ongoing",
                    "relevance_reason": "当前片段明确围绕天气变化与体感展开。",
                },
            ]
            payload = payloads[self.creation_index]
            self.creation_index += 1
            return response_model(**payload)

        if response_model.__name__ == "TopicMergeReviewPayload":
            return response_model(merges=[])

        payload_map = {
            "global_persona_summary": "表达轻松，回应直接。",
            "style_traits": ["简短", "口语化"],
            "conflict_traits": ["先解释后回避"],
            "relationship_specific_patterns": ["会主动接梗"],
            "confidence": 0.77,
            "relationship_temperature": "warm",
            "tension_level": "low",
            "openness_level": "medium",
            "initiative_balance": "balanced",
            "defensiveness_level": "low",
            "unresolved_conflict_flags": [],
            "relationship_phase": "warming",
            "snapshot_summary": "双方维持轻松状态。",
        }
        return response_model(**{key: value for key, value in payload_map.items() if key in response_model.model_fields})


class MergeReviewLLM:
    def __init__(self) -> None:
        self.summary_index = 0
        self.creation_index = 0

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        if response_model.__name__ == "SegmentSummaryPayload":
            payloads = [
                {
                    "summary_text": "双方讨论宿舍申请 timing 卡点。",
                    "main_topics": ["宿舍申请", "timing 卡点"],
                    "self_stance": "继续宿舍申请话题",
                    "other_stance": "抛出 timing 问题",
                    "emotional_tone": "轻松",
                    "interaction_pattern": "轻松吐槽",
                    "has_conflict": False,
                    "has_repair": False,
                    "has_closeness_signal": False,
                    "outcome": "宿舍申请话题继续",
                    "relationship_impact": "neutral_positive",
                    "confidence": 0.83,
                },
                {
                    "summary_text": "双方继续聊宿舍办理规则和流程。",
                    "main_topics": ["宿舍办理流程", "住宿规则"],
                    "self_stance": "顺着规则问题继续聊",
                    "other_stance": "接住宿办理流程",
                    "emotional_tone": "轻松",
                    "interaction_pattern": "日常接话",
                    "has_conflict": False,
                    "has_repair": False,
                    "has_closeness_signal": False,
                    "outcome": "宿舍办理话题继续",
                    "relationship_impact": "neutral_positive",
                    "confidence": 0.81,
                },
                {
                    "summary_text": "双方聊到最近降温和天气变化。",
                    "main_topics": ["天气变化", "降温"],
                    "self_stance": "接住天气话题",
                    "other_stance": "先提到降温",
                    "emotional_tone": "轻松",
                    "interaction_pattern": "日常接话",
                    "has_conflict": False,
                    "has_repair": False,
                    "has_closeness_signal": False,
                    "outcome": "天气话题继续",
                    "relationship_impact": "neutral_positive",
                    "confidence": 0.79,
                },
            ]
            payload = payloads[self.summary_index]
            self.summary_index += 1
            return response_model(**payload)

        if response_model.__name__ == "TopicAssignmentPayload":
            return response_model(matched_topics=[], should_create_new_topic=True)

        if response_model.__name__ == "TopicCreationPayload":
            payloads = [
                {
                    "topic_name": "宿舍申请 timing 问题",
                    "topic_summary": "围绕宿舍申请 timing 卡点的讨论。",
                    "topic_status": "ongoing",
                    "relevance_reason": "当前片段聚焦宿舍申请 timing 问题。",
                },
                {
                    "topic_name": "宿舍办理流程",
                    "topic_summary": "围绕宿舍办理规则和流程的讨论。",
                    "topic_status": "ongoing",
                    "relevance_reason": "当前片段聚焦宿舍办理流程。",
                },
                {
                    "topic_name": "天气相关话题",
                    "topic_summary": "围绕天气变化、气温和体感的讨论。",
                    "topic_status": "ongoing",
                    "relevance_reason": "当前片段明确围绕天气变化展开。",
                },
            ]
            payload = payloads[self.creation_index]
            self.creation_index += 1
            return response_model(**payload)

        if response_model.__name__ == "TopicMergeReviewPayload":
            return response_model(
                merges=[
                    {
                        "source_topic_ids": [1, 2],
                        "merged_topic_name": "宿舍/住宿讨论",
                        "merged_topic_summary": "围绕宿舍、住宿安排、办理流程与相关问题的持续讨论。",
                        "merged_topic_status": "ongoing",
                        "merge_reason": "两个 topic 都属于宿舍/住宿这一中粒度话题，只是局部子问题不同。",
                    }
                ]
            )

        payload_map = {
            "global_persona_summary": "表达轻松，回应直接。",
            "style_traits": ["简短", "口语化"],
            "conflict_traits": ["先解释后回避"],
            "relationship_specific_patterns": ["会主动接梗"],
            "confidence": 0.76,
            "relationship_temperature": "warm",
            "tension_level": "low",
            "openness_level": "medium",
            "initiative_balance": "balanced",
            "defensiveness_level": "low",
            "unresolved_conflict_flags": [],
            "relationship_phase": "warming",
            "snapshot_summary": "双方维持轻松状态。",
        }
        return response_model(**{key: value for key, value in payload_map.items() if key in response_model.model_fields})


class SpyLLM(FakeLLM):
    pass


class FakeSimulationLLM:
    def __init__(self, responses):
        self._responses = responses

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        response = self._responses.pop(0)
        assert isinstance(response, response_model)
        return response


class FailingSimulationLLM:
    def __init__(self, responses, *, fail_on_call_index: int):
        self._responses = responses
        self._call_index = 0
        self._fail_on_call_index = fail_on_call_index

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        if self._call_index == self._fail_on_call_index:
            raise RuntimeError("simulated first_reply failure")
        response = self._responses[self._call_index]
        self._call_index += 1
        assert isinstance(response, response_model)
        return response


def _seed_job(*, fixture_path: Path, job_type: str = "full_analysis", conversation_status: str = "queued"):
    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status=conversation_status,
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(fixture_path),
            source_file_hash="abc123",
            message_count_hint=6,
        )
        session.add(batch)
        session.flush()

        job = AnalysisJob(
            conversation_id=conversation.id,
            job_type=job_type,
            status="queued",
            current_stage="created",
            progress_percent=0,
            retry_count=0,
            payload_json={"import_id": batch.id},
        )
        session.add(job)


def _write_multi_segment_fixture(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "[QQChatExporter V5 / https://github.com/shuakami/qq-chat-exporter]",
                "",
                "聊天名称: 梣ゥ",
                "聊天类型: 私聊",
                "导出时间: 2026-04-01 17:31:41",
                "消息总数: 6",
                "时间范围: 2025-03-02 20:18:03 - 2025-03-02 22:10:01",
                "",
                "",
                "梣ゥ:",
                "时间: 2025-03-02 20:18:03",
                "内容: 第一段开场",
                "",
                "",
                "Tantless:",
                "时间: 2025-03-02 20:18:10",
                "内容: 第一段回应",
                "",
                "",
                "梣ゥ:",
                "时间: 2025-03-02 21:00:00",
                "内容: 第二段开场",
                "",
                "",
                "Tantless:",
                "时间: 2025-03-02 21:00:10",
                "内容: 第二段回应",
                "",
                "",
                "梣ゥ:",
                "时间: 2025-03-02 22:10:00",
                "内容: 第三段开场",
                "",
                "",
                "Tantless:",
                "时间: 2025-03-02 22:10:01",
                "内容: 第三段回应",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_run_next_job_parses_messages_and_creates_analysis_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    processed = run_next_job(llm_client=FakeLLM())

    assert processed is True

    with session_scope() as session:
        assert session.query(Message).count() == 6
        sequence_numbers = [message.sequence_no for message in session.query(Message).order_by(Message.sequence_no.asc()).all()]
        assert sequence_numbers == [1, 2, 3, 4, 5, 6]
        assert all(message.import_id == 1 for message in session.query(Message).all())
        assert session.query(Segment).count() >= 1
        assert session.query(SegmentSummary).count() >= 1
        assert session.query(Topic).count() == 1
        assert session.query(PersonaProfile).count() == 2
        assert session.query(RelationshipSnapshot).count() >= 1
        job = session.query(AnalysisJob).one()
        assert job.status == "completed"
        assert job.current_stage == "completed"
        assert job.progress_percent == 100
        progress = job.payload_json["progress"]
        assert progress["overall_total_units"] == 6 + 4 * session.query(Segment).count() + 3
        assert progress["overall_completed_units"] == progress["overall_total_units"]
        assert progress["current_stage_total_units"] == progress["overall_total_units"]
        assert progress["current_stage_completed_units"] == progress["overall_completed_units"]
        assert progress["status_message"].startswith("completed ")
        conversation = session.query(Conversation).one()
        assert conversation.status == "ready"


def test_run_next_job_records_analysis_performance_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = tmp_path / "timed_segments.txt"
    _write_multi_segment_fixture(fixture_path)
    init_db()
    _seed_job(fixture_path=fixture_path)

    current_time = {"value": 0.0}
    lines: list[str] = []

    def advance_time(seconds: float) -> None:
        current_time["value"] += seconds

    reporter = ConsoleProgressReporter(
        printer=lines.append,
        time_fn=lambda: current_time["value"],
        max_interval_seconds=30,
    )

    processed = run_next_job(
        llm_client=TimedLLM(advance_time),
        progress_reporter=reporter,
    )

    assert processed is True

    with session_scope() as session:
        job = session.query(AnalysisJob).one()
        performance = job.payload_json["performance"]
        assert performance["input_counts"] == {"messages": 6, "segments": 3}
        assert performance["llm_call_counts"] == {
            "segment_summary": 3,
            "topic_assignment": 3,
            "topic_creation": 1,
            "topic_merge_review": 1,
            "persona": 2,
            "relationship_snapshot": 3,
            "total": 13,
        }
        assert performance["elapsed_seconds"] == 88.0
        assert performance["stage_elapsed_seconds"]["summarizing"] == 6.0
        assert performance["stage_elapsed_seconds"]["topic_resolution"] == 14.0
        assert performance["stage_elapsed_seconds"]["topic_merge_review"] == 7.0
        assert performance["stage_elapsed_seconds"]["persona"] == 22.0
        assert performance["stage_elapsed_seconds"]["snapshots"] == 39.0

    assert any("elapsed=88.0s" in line for line in lines)


def test_run_next_job_completes_import_only_without_analysis_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path, job_type="import_only", conversation_status="imported")

    processed = run_next_job(llm_client=FakeLLM())

    assert processed is True

    with session_scope() as session:
        assert session.query(Message).count() == 6
        assert session.query(Segment).count() == 0
        assert session.query(SegmentSummary).count() == 0
        assert session.query(Topic).count() == 0
        assert session.query(PersonaProfile).count() == 0
        assert session.query(RelationshipSnapshot).count() == 0
        job = session.query(AnalysisJob).one()
        assert job.status == "completed"
        assert job.current_stage == "completed"
        assert job.job_type == "import_only"
        assert job.payload_json["progress"]["status_message"] == "imported 6 messages"
        conversation = session.query(Conversation).one()
        assert conversation.status == "imported"


def test_run_next_job_creates_multiple_topics_and_multi_topic_links(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = tmp_path / "multi_topic_segments.txt"
    _write_multi_segment_fixture(fixture_path)
    init_db()
    _seed_job(fixture_path=fixture_path)

    processed = run_next_job(llm_client=MultiTopicLLM())

    assert processed is True

    with session_scope() as session:
        topics = session.query(Topic).order_by(Topic.id.asc()).all()
        assert [topic.topic_name for topic in topics] == ["宿舍/住宿讨论", "天气相关话题"]
        assert [topic.segment_count for topic in topics] == [2, 2]

        links = session.query(TopicLink).order_by(TopicLink.topic_id.asc(), TopicLink.segment_id.asc()).all()
        assert len(links) == 4
        assert {(link.topic_id, link.segment_id) for link in links} == {(1, 1), (1, 3), (2, 2), (2, 3)}


def test_run_next_job_merges_narrow_topics_into_mid_grain_topics(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = tmp_path / "merge_topic_segments.txt"
    _write_multi_segment_fixture(fixture_path)
    init_db()
    _seed_job(fixture_path=fixture_path)

    processed = run_next_job(llm_client=MergeReviewLLM())

    assert processed is True

    with session_scope() as session:
        topics = session.query(Topic).order_by(Topic.id.asc()).all()
        assert [topic.topic_name for topic in topics] == ["宿舍/住宿讨论", "天气相关话题"]
        assert topics[0].segment_count == 2
        assert topics[0].topic_summary == "围绕宿舍、住宿安排、办理流程与相关问题的持续讨论。"
        assert topics[1].segment_count == 1

        links = session.query(TopicLink).order_by(TopicLink.topic_id.asc(), TopicLink.segment_id.asc()).all()
        assert {(link.topic_id, link.segment_id) for link in links} == {
            (topics[0].id, 1),
            (topics[0].id, 2),
            (topics[1].id, 3),
        }


def test_run_next_job_marks_job_failed_when_stage_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    processed = run_next_job(llm_client=ExplodingLLM())

    assert processed is True

    with session_scope() as session:
        job = session.query(AnalysisJob).one()
        assert job.status == "failed"
        assert job.current_stage == "failed"
        assert job.progress_percent > 0
        assert "boom" in job.error_message
        assert session.query(Message).count() == 0
        assert session.query(Segment).count() == 0
        assert session.query(SegmentSummary).count() == 0
        assert session.query(Topic).count() == 0
        assert session.query(PersonaProfile).count() == 0
        assert session.query(RelationshipSnapshot).count() == 0
        conversation = session.query(Conversation).one()
        assert conversation.status == "failed"


def test_run_next_job_builds_worker_client_from_saved_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    with session_scope() as session:
        session.add_all(
            [
                AppSetting(setting_key="llm.base_url", setting_value="https://db.example/v1", is_secret=False),
                AppSetting(setting_key="llm.api_key", setting_value="db-key", is_secret=True),
                AppSetting(setting_key="llm.chat_model", setting_value="db-model", is_secret=False),
            ]
        )

    built_roles: list[tuple[str, dict[str, str]]] = []
    monkeypatch.setattr(
        "if_then_mvp.worker.build_runtime_llm_client",
        lambda role, settings_map=None: built_roles.append((role, dict(settings_map or {}))) or SpyLLM(),
    )

    processed = run_next_job()

    assert processed is True
    assert built_roles
    assert built_roles[0][0] == "worker"
    assert built_roles[0][1]["llm.chat_model"] == "db-model"


def test_run_next_job_leaves_queued_job_untouched_when_worker_config_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    def raise_missing_config(*, role, settings_map=None):
        raise RuntimeError("worker LLM is not configured")

    monkeypatch.setattr("if_then_mvp.worker.build_runtime_llm_client", raise_missing_config)

    processed = run_next_job()

    assert processed is False

    with session_scope() as session:
        job = session.query(AnalysisJob).one()
        assert job.status == "queued"
        assert job.current_stage == "created"
        assert job.progress_percent == 0
        assert job.error_message is None
        conversation = session.query(Conversation).one()
        assert conversation.status == "queued"


def test_run_next_job_allows_import_only_without_worker_model_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path, job_type="import_only", conversation_status="imported")

    def raise_missing_config(*, role, settings_map=None):
        raise RuntimeError("worker LLM is not configured")

    monkeypatch.setattr("if_then_mvp.worker.build_runtime_llm_client", raise_missing_config)

    processed = run_next_job()

    assert processed is True

    with session_scope() as session:
        job = session.query(AnalysisJob).one()
        assert job.status == "completed"
        assert job.current_stage == "completed"
        assert job.error_message is None
        conversation = session.query(Conversation).one()
        assert conversation.status == "imported"
        assert session.query(Message).count() > 0


def test_claim_next_job_is_single_use_and_marks_conversation_analyzing(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    first_claim = _claim_next_job()
    second_claim = _claim_next_job()

    assert first_claim == (1, 1)
    assert second_claim is None

    with session_scope() as session:
        job = session.query(AnalysisJob).one()
        assert job.status == "running"
        assert job.current_stage == "parsing"
        assert job.progress_percent == 0
        conversation = session.query(Conversation).one()
        assert conversation.status == "analyzing"


def test_console_progress_reporter_emits_on_threshold_and_timeout():
    timestamps = iter([0.0, 1.0, 2.0, 35.0, 36.0])
    lines: list[str] = []
    reporter = ConsoleProgressReporter(
        printer=lines.append,
        time_fn=lambda: next(timestamps),
        max_interval_seconds=30,
    )

    reporter.maybe_emit(
        ProgressSnapshot(
            job_id=7,
            current_stage="parsing",
            progress_percent=0,
            current_stage_completed_units=0,
            current_stage_total_units=1000,
            overall_completed_units=0,
            overall_total_units=2500,
            status_message="parsing 0/1000 messages",
        )
    )
    reporter.maybe_emit(
        ProgressSnapshot(
            job_id=7,
            current_stage="parsing",
            progress_percent=8,
            current_stage_completed_units=200,
            current_stage_total_units=1000,
            overall_completed_units=200,
            overall_total_units=2500,
            status_message="parsing 200/1000 messages",
        )
    )
    reporter.maybe_emit(
        ProgressSnapshot(
            job_id=7,
            current_stage="parsing",
            progress_percent=20,
            current_stage_completed_units=500,
            current_stage_total_units=1000,
            overall_completed_units=500,
            overall_total_units=2500,
            status_message="parsing 500/1000 messages",
        )
    )
    reporter.maybe_emit(
        ProgressSnapshot(
            job_id=7,
            current_stage="parsing",
            progress_percent=24,
            current_stage_completed_units=600,
            current_stage_total_units=1000,
            overall_completed_units=600,
            overall_total_units=2500,
            status_message="parsing 600/1000 messages",
        )
    )
    reporter.maybe_emit(
        ProgressSnapshot(
            job_id=7,
            current_stage="completed",
            progress_percent=100,
            current_stage_completed_units=2500,
            current_stage_total_units=2500,
            overall_completed_units=2500,
            overall_total_units=2500,
            status_message="completed 2500/2500 units",
        )
    )

    assert len(lines) == 4
    assert "job=7 stage=parsing overall=0%" in lines[0]
    assert "500/1000 messages" in lines[1]
    assert "600/1000 messages" in lines[2]
    assert "stage=completed overall=100%" in lines[3]


def test_run_next_job_emits_timeout_heartbeat_during_slow_summaries(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = tmp_path / "slow_segments.txt"
    _write_multi_segment_fixture(fixture_path)
    init_db()
    _seed_job(fixture_path=fixture_path)

    current_time = {"value": 0.0}
    lines: list[str] = []

    def advance_time(seconds: float) -> None:
        current_time["value"] += seconds

    reporter = ConsoleProgressReporter(
        printer=lines.append,
        time_fn=lambda: current_time["value"],
        max_interval_seconds=30,
    )

    processed = run_next_job(
        llm_client=SlowSummaryLLM(advance_time),
        progress_reporter=reporter,
    )

    assert processed is True
    summarizing_lines = [line for line in lines if "stage=summarizing" in line]
    assert any("summarizing 1/3 summaries" in line for line in summarizing_lines)


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
                payload_json={
                    "progress": {
                        "current_stage_total_units": 4,
                        "current_stage_completed_units": 0,
                        "overall_total_units": 4,
                        "overall_completed_units": 0,
                        "status_message": "queued 0/4 steps",
                    }
                },
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
        assert session.query(SimulationTurn).count() == 2
        assert [turn.turn_index for turn in session.query(SimulationTurn).order_by(SimulationTurn.turn_index.asc()).all()] == [1, 2]


def test_run_next_simulation_job_marks_failed_and_rolls_back_partial_rows(tmp_path, monkeypatch):
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
                payload_json={
                    "progress": {
                        "current_stage_total_units": 2,
                        "current_stage_completed_units": 0,
                        "overall_total_units": 2,
                        "overall_completed_units": 0,
                        "status_message": "queued 0/2 steps",
                    }
                },
            )
        )

    processed = run_next_simulation_job(
        llm_client=FailingSimulationLLM(
            [
                BranchAssessmentPayload(
                    branch_direction="closer",
                    state_shift_summary="新说法缓和了互动压力。",
                    other_immediate_feeling="更放松",
                    reply_strategy="light_follow_up",
                    risk_flags=[],
                    confidence=0.8,
                ),
            ],
            fail_on_call_index=1,
        )
    )

    assert processed is True

    with session_scope() as session:
        job = session.query(SimulationJob).one()
        assert job.status == "failed"
        assert job.result_simulation_id is None
        assert job.error_message == "simulated first_reply failure"
        assert session.query(Simulation).count() == 0
        assert session.query(SimulationTurn).count() == 0
