import os
import sys
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent.agent import run_agent  # noqa: E402
from agent.config import get_missing_env_keys  # noqa: E402
from agent.errors import AgentServiceError, friendly_agent_error  # noqa: E402

app = FastAPI()
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    mode: str = "full"
    history: list = Field(default_factory=list)


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
    return {"status": "ok"}


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
        result = run_agent(body.prompt.strip(), mode=body.mode, chat_history=body.history)
        return {
            "output": result.output,
            "model_used": result.model_used,
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
