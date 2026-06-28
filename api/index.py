import os
import sys
import traceback

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent.agent import run_agent  # noqa: E402
from agent.config import (  # noqa: E402
    get_email_delivery_info,
    get_email_recipients,
    get_missing_env_keys,
)
from agent.context import parse_recipient_string  # noqa: E402
from agent.documents import extract_document  # noqa: E402
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
    prompt: str = Field(..., min_length=1)
    mode: str = "full"
    history: list = Field(default_factory=list)
    email_recipients: str = ""
    documents: list[ChatDocument] = Field(default_factory=list)


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
        "email_recipients": get_email_recipients(),
        "email_count": len(get_email_recipients()),
        "email_delivery": get_email_delivery_info(),
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error": "Filename is required."})

    try:
        data = await file.read()
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
    except Exception as exc:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={"error": f"Could not read document: {exc}"},
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

    try:
        ui_recipients = parse_recipient_string(body.email_recipients)
        recipients = ui_recipients or get_email_recipients() or None
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
