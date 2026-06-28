import os
import re
import sys
import traceback

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MAX_PROMPT_CHARS = 8_000
MAX_CHAT_DOCUMENTS = 5
MAX_TOTAL_DOC_CHARS = 150_000
PROMPT_EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


def merge_recipients_from_prompt(prompt: str, ui_recipients: list[str]) -> list[str]:
    merged = list(ui_recipients)
    known = {email.lower() for email in merged}
    for match in PROMPT_EMAIL_PATTERN.findall(prompt):
        email = match.strip().lower()
        if is_valid_email(email) and email not in known:
            merged.append(email)
            known.add(email)
    return merged

from agent.agent import run_agent  # noqa: E402
from agent.config import (  # noqa: E402
    get_email_config_warnings,
    get_email_delivery_info,
    get_missing_env_keys,
    get_valid_email_recipients,
    is_valid_email,
)
from agent.context import parse_recipient_string  # noqa: E402
from agent.documents import MAX_UPLOAD_BYTES, extract_document  # noqa: E402
from agent.errors import AgentServiceError, friendly_agent_error  # noqa: E402

app = FastAPI()
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ChatDocument(BaseModel):
    filename: str
    text: str
    char_count: int = 0
    truncated: bool = False
    format: str = "text"


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_CHARS)
    mode: str = "full"
    history: list = Field(default_factory=list)
    email_recipients: str = Field(default="", max_length=2_000)
    documents: list[ChatDocument] = Field(default_factory=list)

    @field_validator("documents")
    @classmethod
    def validate_documents(cls, documents: list[ChatDocument]) -> list[ChatDocument]:
        if len(documents) > MAX_CHAT_DOCUMENTS:
            raise ValueError(f"At most {MAX_CHAT_DOCUMENTS} documents per message.")
        total_chars = sum(len(doc.text) for doc in documents)
        if total_chars > MAX_TOTAL_DOC_CHARS:
            raise ValueError("Attached documents exceed the size limit.")
        return documents


@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/health")
def health():
    missing = get_missing_env_keys()
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "missing_env",
                "missing": missing,
                "hint": "Add them in Vercel → Settings → Environment Variables.",
            },
        )
    return {
        "status": "ok",
        "email_recipients": get_valid_email_recipients(),
        "email_count": len(get_valid_email_recipients()),
        "email_delivery": get_email_delivery_info(),
        "config_warnings": get_email_config_warnings(),
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error": "Filename is required."})

    try:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail={"error": f"File exceeds {limit_mb} MB limit."},
            )
        extracted = extract_document(data, file.filename)
        return {
            "filename": extracted.filename,
            "text": extracted.text,
            "char_count": extracted.char_count,
            "truncated": extracted.truncated,
            "format": extracted.format,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={"error": "Could not read document."},
        ) from exc


@app.post("/api/chat")
def chat(body: ChatRequest):
    missing = get_missing_env_keys()
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Missing environment variables: {', '.join(missing)}",
                "hint": "Add them in Vercel → Settings → Environment Variables.",
            },
        )

    if body.mode not in ("search_only", "search_and_code", "full"):
        raise HTTPException(status_code=400, detail={"error": "invalid mode"})

    ui_recipients = parse_recipient_string(body.email_recipients)
    invalid_recipients = [email for email in ui_recipients if not is_valid_email(email)]
    if invalid_recipients:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid email address: {', '.join(invalid_recipients)}"},
        )

    try:
        recipients = merge_recipients_from_prompt(
            body.prompt,
            ui_recipients or get_valid_email_recipients(),
        ) or None
        documents = [doc.model_dump() for doc in body.documents] or None
        result = run_agent(
            body.prompt.strip(),
            mode=body.mode,
            chat_history=body.history,
            email_recipients=recipients,
            documents=documents,
        )
        return {
            "output": result.output,
            "model_used": result.model_used,
            "next_steps": result.next_steps,
            "steps": [
                {"tool": s.tool, "input": s.input, "output": s.output}
                for s in result.steps
            ],
        }
    except AgentServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": str(exc), "hint": exc.hint},
        ) from exc
    except Exception as exc:
        print(traceback.format_exc())
        err = friendly_agent_error(exc)
        raise HTTPException(
            status_code=500,
            detail={"error": str(err), "hint": err.hint},
        ) from exc
