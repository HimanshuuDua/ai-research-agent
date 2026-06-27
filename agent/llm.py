import os

from google.api_core.exceptions import ResourceExhausted
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.config import FALLBACK_MODEL, PRIMARY_MODEL


def create_llm(model: str | None = None, *, temperature: float = 0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model or PRIMARY_MODEL,
        temperature=temperature,
        google_api_key=os.environ["GOOGLE_API_KEY"],
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
