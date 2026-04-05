from email.parser import BytesParser
from email.policy import default
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from if_then_mvp.config import get_settings
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, Conversation, ImportBatch
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.schemas import ConversationRead, ImportResponse, JobRead


def create_app() -> FastAPI:
    app = FastAPI(title="If Then MVP API")

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/imports/qq-text", response_model=ImportResponse, status_code=201)
    async def import_qq_text(request: Request) -> ImportResponse:
        settings = get_settings()
        upload_name, self_display_name, raw_bytes = await _parse_import_request(request)
        text = raw_bytes.decode("utf-8")
        parsed = parse_qq_export(text=text, self_display_name=self_display_name)

        if parsed.chat_type != "私聊":
            raise HTTPException(status_code=400, detail="Only private chats are supported")

        uploads_dir = settings.data_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        destination = uploads_dir / upload_name
        destination.write_bytes(raw_bytes)

        with session_scope() as session:
            conversation = Conversation(
                title=parsed.chat_name or "unknown",
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
                source_file_name=upload_name,
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

            return ImportResponse(
                conversation=ConversationRead.model_validate(conversation, from_attributes=True),
                job=JobRead.model_validate(job, from_attributes=True),
            )

    return app


async def _parse_import_request(request: Request) -> tuple[str, str, bytes]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        raise HTTPException(status_code=400, detail="Expected multipart form upload")

    body = await request.body()
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise HTTPException(status_code=400, detail="Invalid multipart payload")

    file_name: str | None = None
    file_bytes: bytes | None = None
    self_display_name: str | None = None

    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue

        field_name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True) or b""

        if field_name == "self_display_name":
            charset = part.get_content_charset() or "utf-8"
            self_display_name = payload.decode(charset).strip()
        elif field_name == "file":
            file_name = Path(part.get_filename() or "qq_export.txt").name
            file_bytes = payload

    if not self_display_name:
        raise HTTPException(status_code=400, detail="self_display_name is required")
    if file_bytes is None:
        raise HTTPException(status_code=400, detail="file is required")

    return file_name or "qq_export.txt", self_display_name, file_bytes
