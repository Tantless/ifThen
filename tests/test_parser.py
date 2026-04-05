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


def test_parse_qq_export_keeps_triple_marker_continuation_inside_body():
    text = (
        "聊天名称: 梣ゥ\n"
        "聊天类型: 私聊\n"
        "消息总数: 2\n"
        "\n"
        "Alice:\n"
        "时间: 2025-03-02 20:19:00\n"
        "内容: 第一行正文\n"
        "\n"
        "Bob:\n"
        "时间: 2025-03-02 20:19:00\n"
        "内容: 这三行其实都还是正文\n"
        "\n"
        "梣ゥ:\n"
        "时间: 2025-03-02 20:19:29\n"
        "内容: 好的\n"
    )

    parsed = parse_qq_export(text=text, self_display_name="Tantless")

    assert len(parsed.messages) == 2
    assert parsed.messages[0].speaker_name == "Alice"
    assert parsed.messages[0].content_text == (
        "第一行正文\n"
        "\n"
        "Bob:\n"
        "时间: 2025-03-02 20:19:00\n"
        "内容: 这三行其实都还是正文"
    )
    assert parsed.messages[1].speaker_name == "梣ゥ"


def test_parse_qq_export_keeps_middle_message_when_body_contains_false_block():
    text = (
        "聊天名称: 梣ゥ\n"
        "聊天类型: 私聊\n"
        "消息总数: 3\n"
        "\n"
        "Alice:\n"
        "时间: 2025-03-02 20:19:00\n"
        "内容: 第一条消息\n"
        "\n"
        "Bob:\n"
        "时间: 2025-03-02 20:19:20\n"
        "内容: 这是 Bob 的正文第一行\n"
        "\n"
        "Mallory:\n"
        "时间: 2025-03-02 20:19:30\n"
        "内容: 这些标记其实还是 Bob 的正文\n"
        "Bob 的正文最后一行\n"
        "\n"
        "Carol:\n"
        "时间: 2025-03-02 20:19:50\n"
        "内容: 最后一条真实消息\n"
    )

    parsed = parse_qq_export(text=text, self_display_name="Tantless")

    assert [message.speaker_name for message in parsed.messages] == ["Alice", "Bob", "Carol"]
    assert parsed.messages[1].content_text == (
        "这是 Bob 的正文第一行\n"
        "\n"
        "Mallory:\n"
        "时间: 2025-03-02 20:19:30\n"
        "内容: 这些标记其实还是 Bob 的正文\n"
        "Bob 的正文最后一行"
    )


def test_parse_qq_export_keeps_final_message_when_body_contains_false_block():
    text = (
        "聊天名称: 梣ゥ\n"
        "聊天类型: 私聊\n"
        "消息总数: 2\n"
        "\n"
        "Alice:\n"
        "时间: 2025-03-02 20:19:00\n"
        "内容: 第一条消息\n"
        "\n"
        "Bob:\n"
        "时间: 2025-03-02 20:19:20\n"
        "内容: 这是最后一条真实消息\n"
        "\n"
        "Mallory:\n"
        "时间: 2025-03-02 20:19:30\n"
        "内容: 这些标记其实还是 Bob 的正文\n"
    )

    parsed = parse_qq_export(text=text, self_display_name="Tantless")

    assert [message.speaker_name for message in parsed.messages] == ["Alice", "Bob"]
    assert parsed.messages[1].content_text == (
        "这是最后一条真实消息\n"
        "\n"
        "Mallory:\n"
        "时间: 2025-03-02 20:19:30\n"
        "内容: 这些标记其实还是 Bob 的正文"
    )
