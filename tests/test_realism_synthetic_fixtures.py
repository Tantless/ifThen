from pathlib import Path
import importlib.util
import re
import sys

from if_then_mvp.parser import parse_qq_export


FIXTURE_ROOT = Path("tests/fixtures/realism_synthetic")
VALIDATOR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_realism_synthetic_corpus.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location("validate_realism_synthetic_corpus", VALIDATOR_PATH)
assert VALIDATOR_SPEC is not None
assert VALIDATOR_SPEC.loader is not None
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
sys.modules[VALIDATOR_SPEC.name] = validator
VALIDATOR_SPEC.loader.exec_module(validator)

EXPECTED_WAIVED_REALISM_DEBT = {
    "case-01-hidden-trauma-confession:repeated-clue:别对我太好",
    "case-02-conflict-repair:future-evidence-before-reveal:T1",
    "case-03-missed-window:early-sleep-cue:2026-03-26 19:23:25",
}

CASES = {
    "case-01-hidden-trauma-confession": {
        "chat_name": "小禾",
        "anchors": [
            "那你以后就归我管了？",
            "你别总逃，我都这么明显了",
            "我喜欢你，你能不能做我女朋友",
            "以前那段关系让我一被确定就想逃",
        ],
    },
    "case-02-conflict-repair": {
        "chat_name": "小棠",
        "anchors": [
            "你别想太多，先把能做的做了",
            "我今天真的撑不住了，你能不能先别分析",
            "我开个玩笑，你别把自己绷这么紧",
            "你这就是压力管理没做好吧",
            "那天我妈检查还没出结果，组里又临时返工",
        ],
    },
    "case-03-missed-window": {
        "chat_name": "阿岚",
        "anchors": [
            "你要不要来陪我走一圈",
            "你找室友吧哈哈，我怕我走太慢",
            "这家店两个人套餐好像刚好",
            "那你快睡，睡着就不想了",
            "后来几次也是，我不是随便问问",
        ],
    },
}


def test_realism_synthetic_conversations_are_parseable_and_anchored():
    for slug, expected in CASES.items():
        conversation_path = FIXTURE_ROOT / slug / "conversation.txt"
        parsed = parse_qq_export(conversation_path.read_text(encoding="utf-8"), self_display_name="我")

        assert parsed.chat_name == expected["chat_name"]
        assert parsed.chat_type == "私聊"
        assert parsed.message_count_hint == len(parsed.messages)
        assert len(parsed.messages) >= 1000
        assert {message.speaker_role for message in parsed.messages} <= {"self", "other"}
        assert all(message.message_type == "text" for message in parsed.messages)
        assert [message.timestamp for message in parsed.messages] == sorted(
            message.timestamp for message in parsed.messages
        )

        contents = {message.content_text for message in parsed.messages}
        for anchor in expected["anchors"]:
            assert anchor in contents

        joined_content = "\n".join(message.content_text for message in parsed.messages)
        assert not re.search(r"https?://|www\.|微信号|QQ号|手机号|身份证", joined_content, flags=re.IGNORECASE)


def test_realism_synthetic_metadata_documents_evaluation_contract():
    required_files = {
        "conversation.txt",
        "timeline.md",
        "rewrite-points.md",
        "truth-after-cutoff.md",
        "generation-notes.md",
    }

    for slug in CASES:
        case_dir = FIXTURE_ROOT / slug
        assert required_files <= {path.name for path in case_dir.iterdir()}

        rewrite_points = (case_dir / "rewrite-points.md").read_text(encoding="utf-8")
        truth_after_cutoff = (case_dir / "truth-after-cutoff.md").read_text(encoding="utf-8")
        generation_notes = (case_dir / "generation-notes.md").read_text(encoding="utf-8")

        assert rewrite_points.count("## RP") >= 3
        assert "cutoff-only 评估" in rewrite_points
        assert "modeler-only evidence" in rewrite_points
        assert "modeler-only evidence" in truth_after_cutoff
        assert "是否通过：True" in generation_notes


def test_realism_synthetic_quality_audit_has_no_unwaived_findings():
    report = validator.build_report(FIXTURE_ROOT)

    assert report["status"] == "passed"
    assert report["summary"]["unwaived_finding_count"] == 0
    waived_keys = {finding["key"] for finding in report["findings"] if finding["waived"]}
    assert waived_keys == EXPECTED_WAIVED_REALISM_DEBT


def test_realism_synthetic_validator_fails_unwaived_temporal_defects(tmp_path):
    case_dir = tmp_path / "case-unwaived"
    case_dir.mkdir()
    (case_dir / "conversation.txt").write_text(
        "\n".join(
            [
                "[QQChatExporter V5 / https://github.com/shuakami/qq-chat-exporter]",
                "",
                "聊天名称: 小禾",
                "聊天类型: 私聊",
                "导出时间: 2026-05-02 20:00:00",
                "消息总数: 2",
                "时间范围: 2026-05-03 10:00:00 - 2026-05-03 21:00:00",
                "",
                "",
                "我:",
                "时间: 2026-05-03 10:00:00",
                "内容: 早",
                "",
                "小禾:",
                "时间: 2026-05-03 21:00:00",
                "内容: 今天先撑过上午",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = validator.build_report(tmp_path)

    assert report["status"] == "failed"
    unwaived = {finding["check_id"] for finding in report["findings"] if not finding["waived"]}
    assert {"export-time-before-last-message", "morning-reference-after-noon"} <= unwaived
