import os
import re
import sys
import traceback

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
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

from agent.agent import AgentStep, email_status_from_steps, run_agent  # noqa: E402
from agent.config import (  # noqa: E402
    get_email_config_warnings,
    get_email_delivery_info,
    get_email_provider,
    get_missing_env_keys,
    get_valid_email_recipients,
    is_valid_email,
)
from agent.context import parse_recipient_string  # noqa: E402
from agent.documents import MAX_UPLOAD_BYTES, extract_document  # noqa: E402
from agent.email_delivery import deliver_email, verify_smtp_login  # noqa: E402
from agent.errors import AgentServiceError, friendly_agent_error  # noqa: E402
from agent.security import redact_env_values, sanitize_assistant_output  # noqa: E402
from agent.storage import (  # noqa: E402
    append_message,
    get_session_messages,
    init_db,
    log_usage,
    session_key_from_request,
)

init_db()
app = FastAPI()
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _session_context(request: Request) -> tuple[str, str]:
    ip = _client_ip(request)
    session_key = session_key_from_request(ip, request.headers.get("user-agent", ""))
    ip_hash = session_key[:16]
    return session_key, ip_hash


def _email_was_sent(steps: list) -> bool:
    return any(
        step.tool == "send_email" and "sent successfully" in step.output.lower()
        for step in steps
    )


def _ensure_email_delivered(result, recipients: list[str] | None, prompt: str):
    """If the agent's send_email tool failed, deliver via SMTP/API directly."""
    if not recipients or _email_was_sent(result.steps):
        return result

    subject = prompt.strip()[:100] or "Research summary"
    try:
        message = deliver_email(
            recipients,
            f"AI Research Agent: {subject[:70]}",
            result.output,
        )
        result.steps.append(
            AgentStep(
                tool="send_email",
                input=f"server fallback → {', '.join(recipients)}",
                output=message,
            )
        )
        if any(
            phrase in result.output.lower()
            for phrase in ("cannot send", "encountered an error", "issue with the email")
        ):
            result.output = f"{result.output.rstrip()}\n\n{message}"
    except AgentServiceError as exc:
        detail = str(exc)
        if exc.hint:
            detail = f"{detail} Hint: {exc.hint}"
        result.steps.append(
            AgentStep(
                tool="send_email",
                input=f"server fallback → {', '.join(recipients)}",
                output=f"Error: {detail}",
            )
        )
        result.output = f"{result.output.rstrip()}\n\nEmail delivery failed: {detail}"
    return result


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
    from agent.email_delivery import get_email_pool_size
    from agent.key_pool import get_google_api_keys
    from agent.storage import supabase_ping, use_supabase

    gemini_keys = get_google_api_keys()
    email_pool = get_email_pool_size()
    return {
        "status": "ok",
        "email_delivery": get_email_delivery_info(),
        "config_warnings": get_email_config_warnings(),
        "multi_key_support": True,
        "gemini_key_count": len(gemini_keys),
        "gemini_rotation_ready": len(gemini_keys) > 1,
        "email_account_count": email_pool,
        "email_rotation_ready": email_pool > 1,
        "storage_backend": "supabase" if use_supabase() else "sqlite",
        "supabase": supabase_ping(),
    }


@app.get("/api/session/history")
def session_history(request: Request):
    session_key, _ = _session_context(request)
    messages = get_session_messages(session_key)
    return {
        "session_key": session_key[:8],
        "messages": [
            {
                "role": m["role"],
                "content": m["content"],
                "mode": m.get("mode"),
                "model_used": m.get("model_used"),
            }
            for m in messages
        ],
    }


@app.get("/api/email/ping")
def email_ping():
    missing = get_missing_env_keys()
    if missing:
        raise HTTPException(
            status_code=503,
            detail={"error": f"Missing: {', '.join(missing)}"},
        )

    provider = get_email_provider()
    if provider == "smtp":
        result = verify_smtp_login()
        return {"provider": "smtp", **result}
    if provider == "brevo":
        return {
            "provider": "brevo",
            "ok": True,
            "hint": "Brevo uses HTTP API — no SMTP login test needed.",
        }
    return {
        "provider": provider,
        "ok": True,
        "hint": "Resend uses HTTP API — no SMTP login test needed.",
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
def chat(body: ChatRequest, request: Request):
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
        recipients = merge_recipients_from_prompt(body.prompt, ui_recipients) or None
        if body.mode == "full" and not recipients:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Add your email address before sending.",
                    "hint": "Enter your email in the composer or settings panel.",
                },
            )
        documents = [doc.model_dump() for doc in body.documents] or None
        session_key, ip_hash = _session_context(request)
        append_message(
            session_key,
            ip_hash,
            "user",
            redact_env_values(body.prompt.strip()),
            mode=body.mode,
        )
        result = run_agent(
            body.prompt.strip(),
            mode=body.mode,
            chat_history=body.history,
            email_recipients=recipients,
            documents=documents,
        )
        if body.mode == "full":
            result = _ensure_email_delivered(result, recipients, body.prompt.strip())
        email_status = email_status_from_steps(result.steps)
        safe_output = sanitize_assistant_output(result.output)
        append_message(
            session_key,
            ip_hash,
            "assistant",
            redact_env_values(safe_output),
            mode=body.mode,
            model_used=result.model_used,
        )
        log_usage(
            session_key,
            ip_hash,
            redact_env_values(body.prompt.strip()),
            redact_env_values(safe_output),
            mode=body.mode,
            model_used=result.model_used,
            email_status=email_status,
        )
        return {
            "output": safe_output,
            "model_used": result.model_used,
            "next_steps": result.next_steps,
            "email_status": email_status,
            "session_key": session_key[:8],
            "steps": [
                {"tool": s.tool, "input": s.input, "output": s.output}
                for s in result.steps
            ],
        }
    except HTTPException:
        raise
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
