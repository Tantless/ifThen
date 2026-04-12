from if_then_mvp.sim_cli import main


def test_list_self_text_supports_keywords_and_limit(monkeypatch, capsys):
    pages = [
        [
            {
                "id": 1,
                "sequence_no": 1,
                "speaker_role": "other",
                "timestamp": "2025-03-02T20:18:03",
                "content_text": "你好呀",
                "message_type": "text",
            },
            {
                "id": 2,
                "sequence_no": 2,
                "speaker_role": "self",
                "timestamp": "2025-03-02T20:18:04",
                "content_text": "你好",
                "message_type": "text",
            },
            {
                "id": 3,
                "sequence_no": 3,
                "speaker_role": "self",
                "timestamp": "2025-03-02T20:18:05",
                "content_text": "晚安",
                "message_type": "text",
            },
        ],
        [
            {
                "id": 4,
                "sequence_no": 4,
                "speaker_role": "self",
                "timestamp": "2025-03-02T20:18:06",
                "content_text": "再次说你好",
                "message_type": "text",
            },
            {
                "id": 5,
                "sequence_no": 5,
                "speaker_role": "self",
                "timestamp": "2025-03-02T20:18:07",
                "content_text": "[图片: a.jpg]",
                "message_type": "image",
            },
        ],
        [],
    ]

    def fake_fetch_messages_page(*, base_url, conversation_id, after, page_size):
        assert base_url == "http://127.0.0.1:8000"
        assert conversation_id == 5
        assert page_size == 200
        return pages.pop(0)

    monkeypatch.setattr("if_then_mvp.sim_cli.fetch_messages_page", fake_fetch_messages_page)

    exit_code = main(
        [
            "list-self-text",
            "--conversation-id",
            "5",
            "--keywords",
            "你好",
            "--limit",
            "2",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "id=2 seq=2 time=2025-03-02T20:18:04 text=你好",
        "id=4 seq=4 time=2025-03-02T20:18:06 text=再次说你好",
    ]


def test_simulate_posts_payload_and_prints_job_metadata(monkeypatch, capsys):
    recorded = {}

    def fake_post_json(*, base_url, path, payload):
        recorded["base_url"] = base_url
        recorded["path"] = path
        recorded["payload"] = payload
        return {
            "id": 42,
            "conversation_id": 5,
            "target_message_id": 13,
            "mode": "short_thread",
            "turn_count": 4,
            "status": "queued",
            "current_stage": "queued",
            "progress_percent": 0,
            "status_message": "等待 worker 处理",
            "result_simulation_id": None,
        }

    monkeypatch.setattr("if_then_mvp.sim_cli.post_json", fake_post_json)

    exit_code = main(
        [
            "simulate",
            "--conversation-id",
            "5",
            "--target-message-id",
            "13",
            "--replacement",
            "如果现在不太方便也没关系，等你方便的时候再说就好。",
            "--mode",
            "short_thread",
            "--turn-count",
            "4",
        ]
    )

    assert exit_code == 0
    assert recorded == {
        "base_url": "http://127.0.0.1:8000",
        "path": "/simulations",
        "payload": {
            "conversation_id": 5,
            "target_message_id": 13,
            "replacement_content": "如果现在不太方便也没关系，等你方便的时候再说就好。",
            "mode": "short_thread",
            "turn_count": 4,
        },
    }
    assert capsys.readouterr().out.splitlines() == [
        "id=42 conversation_id=5",
        "target_message_id=13 mode=short_thread",
        "turn_count=4 status=queued",
        "current_stage=queued progress_percent=0",
        "status_message=等待 worker 处理",
        "result_simulation_id=None",
    ]
