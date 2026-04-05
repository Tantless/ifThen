from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from if_then_mvp.config import get_settings
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, Conversation, ImportBatch
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.schemas import ConversationRead, ImportResponse, JobRead

INVALID_TEXT_DETAIL = "Uploaded file must be valid UTF-8 text"
INVALID_EXPORT_DETAIL = "Uploaded file must be a valid QQ private chat export"


def create_app() -> FastAPI:
    app = FastAPI(title="If Then MVP API")

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/imports/qq-text", response_model=ImportResponse, status_code=201)
    async def import_qq_text(file: UploadFile = File(...), self_display_name: str = Form(...)) -> ImportResponse:
        settings = get_settings()
        raw_bytes = await file.read()

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail=INVALID_TEXT_DETAIL) from exc

        parsed = parse_qq_export(text=text, self_display_name=self_display_name)
        if parsed.chat_type != "私聊" or not parsed.chat_name or not parsed.messages:
            raise HTTPException(status_code=400, detail=INVALID_EXPORT_DETAIL)

        uploads_dir = settings.data_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        destination = uploads_dir / _generate_storage_name()
        source_file_name = file.filename or "qq_export.txt"

        try:
            destination.write_bytes(raw_bytes)

            with session_scope() as session:
                conversation = Conversation(
                    title=parsed.chat_name,
                    chat_type="private",
                    self_display_name=self_display_name,
                    other_display_name=next(
                        (message.speaker_name for message in parsed.messages if message.speaker_role == "other"),
                        "unknown",
                    ),
                    source_format="qq_chat_exporter_v5",
                    status="queued",
                )
                session.add(conversation)
                session.flush()

                batch = ImportBatch(
                    conversation_id=conversation.id,
                    source_file_name=source_file_name,
                    source_file_path=str(destination),
                    source_file_hash=sha256(raw_bytes).hexdigest(),
                    message_count_hint=parsed.message_count_hint,
                )
                session.add(batch)
                session.flush()

                job = AnalysisJob(
                    conversation_id=conversation.id,
                    job_type="full_analysis",
                    status="queued",
                    current_stage="created",
                    progress_percent=0,
                    retry_count=0,
                    payload_json={"import_id": batch.id},
                )
                session.add(job)
                session.flush()

                response = ImportResponse(
                    conversation=ConversationRead.model_validate(conversation, from_attributes=True),
                    job=JobRead.model_validate(job, from_attributes=True),
                )
        except Exception:
            _remove_file_if_present(destination)
            raise

        return response

    return app


def _generate_storage_name() -> str:
    return f"qq-import-{uuid4().hex}.txt"


def _remove_file_if_present(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
