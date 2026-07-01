import os

from google.api_core.exceptions import ResourceExhausted
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.config import FALLBACK_MODEL, PRIMARY_MODEL


def _llm_timeout() -> int:
    return int(os.getenv("LLM_TIMEOUT", "22"))


def create_llm(
    model: str | None = None,
    *,
    temperature: float = 0,
    google_api_key: str | None = None,
    streaming: bool = False,
) -> ChatGoogleGenerativeAI:
    api_key = google_api_key or os.environ["GOOGLE_API_KEY"]
    # max_retries=0: don't let LangChain do its slow exponential backoff (2s,4s,8s...).
    # Our own key + model rotation in run_agent handles failures immediately instead.
    return ChatGoogleGenerativeAI(
        model=model or PRIMARY_MODEL,
        temperature=temperature,
        google_api_key=api_key,
        streaming=streaming,
        max_retries=0,
        timeout=_llm_timeout(),
        max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1536")),
    )


def invoke_with_fallback(
    llm: ChatGoogleGenerativeAI,
    messages,
    fallback_model: str = FALLBACK_MODEL,
):
    """Try primary model; on quota errors, retry once with the fallback model."""
    try:
        return llm.invoke(messages), llm.model
    except ResourceExhausted:
        if llm.model == fallback_model:
            raise
        fallback_llm = create_llm(fallback_model, temperature=llm.temperature)
        return fallback_llm.invoke(messages), fallback_model
