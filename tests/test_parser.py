from pathlib import Path

from if_then_mvp.parser import parse_qq_export


def test_parse_qq_export_extracts_messages_and_flags():
    text = Path("tests/fixtures/qq_export_sample.txt").read_text(encoding="utf-8")

    parsed = parse_qq_export(text=text, self_display_name="Tantless")

    assert parsed.chat_name == "梣ゥ"
    assert parsed.chat_type == "私聊"
    assert parsed.message_count_hint == 6
    assert len(parsed.messages) == 6

    first = parsed.messages[0]
    assert first.speaker_role == "other"
    assert first.message_type == "text"

    image_message = parsed.messages[2]
    assert image_message.message_type == "image"
    assert image_message.resource_items == [{"kind": "image", "name": "1DA1EB4EA41F53A9407923B093C213B6.jpg"}]

    colon_speaker_message = parsed.messages[3]
    assert colon_speaker_message.speaker_name == "A:B"
    assert colon_speaker_message.speaker_role == "other"
    assert colon_speaker_message.content_text == (
        "收到了\n"
        "昵称:\n"
        "\n"
        "Bob:\n"
        "时间: 2025-03-02 20:19:04\n"
        "继续这一条的第二行"
    )

    unknown_message = parsed.messages[5]
    assert unknown_message.speaker_role == "unknown"
    assert "unknown_speaker" in unknown_message.parse_flags


def test_parse_qq_export_preserves_raw_block_and_line_range():
    text = Path("tests/fixtures/qq_export_sample.txt").read_text(encoding="utf-8")

    parsed = parse_qq_export(text=text, self_display_name="Tantless")

    image_message = parsed.messages[2]
    assert image_message.raw_speaker_label == "梣ゥ"
    assert image_message.source_line_start == 13
    assert image_message.source_line_end == 17
    assert image_message.raw_block_text == (
        "梣ゥ:\n"
        "时间: 2025-03-02 20:18:41\n"
        "内容: [图片: 1DA1EB4EA41F53A9407923B093C213B6.jpg]\n"
        "资源:\n"
        "  - image: 1DA1EB4EA41F53A9407923B093C213B6.jpg"
    )
