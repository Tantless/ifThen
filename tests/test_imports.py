from pathlib import Path

from fastapi.testclient import TestClient

from if_then_mvp.api import create_app
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, Conversation, ImportBatch


def test_import_endpoint_persists_upload_and_enqueues_job(tmp_path, monkeypatch):
    uploads_root = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(uploads_root))
    init_db()

    sample_bytes = Path("tests/fixtures/qq_export_sample.txt").read_bytes()

    with TestClient(create_app()) as client:
        response = client.post(
            "/imports/qq-text",
            data={"self_display_name": "Tantless"},
            files={"file": ("聊天记录.txt", sample_bytes, "text/plain")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["conversation"]["title"] == "梣ゥ"
    assert payload["job"]["status"] == "queued"

    upload_path = uploads_root / "uploads" / "聊天记录.txt"
    assert upload_path.exists()
    assert upload_path.read_bytes() == sample_bytes

    with session_scope() as session:
        assert session.query(Conversation).count() == 1
        assert session.query(ImportBatch).count() == 1
        assert session.query(AnalysisJob).count() == 1
