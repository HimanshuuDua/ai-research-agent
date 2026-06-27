from google.api_core.exceptions import ResourceExhausted
from resend.exceptions import ResendError


class AgentServiceError(Exception):
    """Raised when an external service fails with a user-friendly message."""

    def __init__(self, message: str, hint: str | None = None):
        self.hint = hint
        super().__init__(message)


def friendly_agent_error(exc: Exception) -> AgentServiceError:
    message = str(exc)

    if isinstance(exc, ResourceExhausted) or "429" in message or "quota" in message.lower():
        return AgentServiceError(
            "Gemini API quota exceeded. Wait a minute and try again, or use a shorter prompt.",
            hint=(
                "Free tier limits reset daily. "
                "Set GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite in .env."
            ),
        )

    if "API key not valid" in message or "API_KEY_INVALID" in message:
        return AgentServiceError(
            "Invalid Google API key.",
            hint=(
                "Create a key at https://aistudio.google.com/apikey "
                "and set GOOGLE_API_KEY in .env."
            ),
        )

    if "SerpAPI" in message or "serpapi" in message.lower():
        return AgentServiceError(
            "Web search failed. Check your SerpAPI key or monthly search limit.",
            hint="Manage keys at https://serpapi.com/manage-api-key (250 free searches/month).",
        )

    if isinstance(exc, ResendError) or "resend" in message.lower():
        return AgentServiceError(
            "Email delivery failed.",
            hint=(
                "Verify RESEND_API_KEY and use onboarding@resend.dev "
                "only for your own inbox until you verify a domain."
            ),
        )

    if "KeyError" in type(exc).__name__:
        return AgentServiceError(
            "Missing environment variable.",
            hint="Copy .env.example to .env and fill in all required keys.",
        )

    return AgentServiceError(f"Agent error: {message}")
