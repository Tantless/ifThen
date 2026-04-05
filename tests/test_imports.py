from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

import if_then_mvp.api as api_module
from if_then_mvp.api import create_app
from if_then_mvp.db import get_sessionmaker, init_db, session_scope
from if_then_mvp.models import AnalysisJob, Conversation, ImportBatch


def _post_import(client: TestClient, sample_bytes: bytes, filename: str = "聊天记录.txt"):
    return client.post(
        "/imports/qq-text",
        data={"self_display_name": "Tantless"},
        files={"file": (filename, sample_bytes, "text/plain")},
    )


def test_import_endpoint_persists_upload_and_enqueues_job(tmp_path, monkeypatch):
    uploads_root = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(uploads_root))
    init_db()

    sample_bytes = Path("tests/fixtures/qq_export_sample.txt").read_bytes()

    with TestClient(create_app()) as client:
        response = _post_import(client, sample_bytes)

    assert response.status_code == 201
    payload = response.json()
    assert payload["conversation"]["title"] == "梣ゥ"
    assert payload["job"]["status"] == "queued"

    with session_scope() as session:
        assert session.query(Conversation).count() == 1
        assert session.query(ImportBatch).count() == 1
        assert session.query(AnalysisJob).count() == 1
        batch = session.query(ImportBatch).one()

    upload_path = Path(batch.source_file_path)
    assert batch.source_file_name == "聊天记录.txt"
    assert upload_path.parent == uploads_root / "uploads"
    assert upload_path.name != "聊天记录.txt"
    assert upload_path.exists()
    assert upload_path.read_bytes() == sample_bytes


def test_import_endpoint_keeps_distinct_files_for_same_original_filename(tmp_path, monkeypatch):
    uploads_root = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(uploads_root))
    init_db()

    first_bytes = Path("tests/fixtures/qq_export_sample.txt").read_bytes()
    second_text = Path("tests/fixtures/qq_export_sample.txt").read_text(encoding="utf-8").replace("内容: 你好", "内容: 第二次导入", 1)
    second_bytes = second_text.encode("utf-8")

    with TestClient(create_app()) as client:
        first_response = _post_import(client, first_bytes)
        second_response = _post_import(client, second_bytes)

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    with session_scope() as session:
        batches = session.query(ImportBatch).order_by(ImportBatch.id).all()

    assert len(batches) == 2
    assert [batch.source_file_name for batch in batches] == ["聊天记录.txt", "聊天记录.txt"]
    assert batches[0].source_file_path != batches[1].source_file_path
    assert Path(batches[0].source_file_path).name != "聊天记录.txt"
    assert Path(batches[1].source_file_path).name != "聊天记录.txt"
    assert Path(batches[0].source_file_path).read_bytes() == first_bytes
    assert Path(batches[1].source_file_path).read_bytes() == second_bytes


def test_import_endpoint_cleans_up_saved_file_when_transaction_fails(tmp_path, monkeypatch):
    uploads_root = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(uploads_root))
    init_db()

    @contextmanager
    def failing_session_scope():
        session = get_sessionmaker()()
        try:
            yield session
            raise RuntimeError("forced transaction failure")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(api_module, "session_scope", failing_session_scope)
    sample_bytes = Path("tests/fixtures/qq_export_sample.txt").read_bytes()

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = _post_import(client, sample_bytes)

    assert response.status_code == 500
    uploads_dir = uploads_root / "uploads"
    assert not uploads_dir.exists() or list(uploads_dir.iterdir()) == []

    with session_scope() as session:
        assert session.query(Conversation).count() == 0
        assert session.query(ImportBatch).count() == 0
        assert session.query(AnalysisJob).count() == 0


def test_import_endpoint_returns_400_for_invalid_utf8(tmp_path, monkeypatch):
    uploads_root = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(uploads_root))
    init_db()

    with TestClient(create_app()) as client:
        response = _post_import(client, b"\xff\xfe\xfa")

    assert response.status_code == 400
    assert response.json() == {"detail": "Uploaded file must be valid UTF-8 text"}
    uploads_dir = uploads_root / "uploads"
    assert not uploads_dir.exists() or list(uploads_dir.iterdir()) == []

    with session_scope() as session:
        assert session.query(Conversation).count() == 0
        assert session.query(ImportBatch).count() == 0
        assert session.query(AnalysisJob).count() == 0
