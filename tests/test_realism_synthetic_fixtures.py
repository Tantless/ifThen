from pathlib import Path
import re

from if_then_mvp.parser import parse_qq_export


FIXTURE_ROOT = Path("tests/fixtures/realism_synthetic")

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
