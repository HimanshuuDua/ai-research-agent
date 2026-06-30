import smtplib

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

    if (
        "401" in message
        or "ACCESS_TOKEN_TYPE_UNSUPPORTED" in message
        or "invalid authentication credentials" in message.lower()
    ):
        return AgentServiceError(
            "Invalid Google API credentials.",
            hint=(
                "Check GOOGLE_API_KEY for stray characters or labels (e.g. a trailing -1). "
                "Create a fresh key at https://aistudio.google.com/apikey and update it on Vercel."
            ),
        )

    if "SerpAPI" in message or "serpapi" in message.lower():
        return AgentServiceError(
            "Web search failed. Check your SerpAPI key or monthly search limit.",
            hint="Manage keys at https://serpapi.com/manage-api-key (250 free searches/month).",
        )

    if isinstance(exc, smtplib.SMTPException):
        hint = (
            "Check SMTP_USER and SMTP_PASSWORD in .env. For Gmail, use an App Password: "
            "https://myaccount.google.com/apppasswords (requires 2-Step Verification)."
        )
        if "authentication" in message.lower() or "535" in message:
            hint = (
                "Gmail rejected the login. Use an App Password, not your regular password. "
                "Create one at https://myaccount.google.com/apppasswords"
            )
        return AgentServiceError("SMTP email delivery failed.", hint=hint)

    if isinstance(exc, ResendError) or "resend" in message.lower():
        hint = (
            "Resend delivery failed. For sending to any address without domain verification, "
            "switch to Gmail SMTP: EMAIL_PROVIDER=smtp with SMTP_USER and SMTP_PASSWORD."
        )
        if "only send testing emails" in message.lower() or "403" in message:
            hint = (
                "Resend test sender only works for your account email. "
                "Use EMAIL_PROVIDER=smtp with a Gmail App Password instead."
            )
        return AgentServiceError("Email delivery failed.", hint=hint)

    if "KeyError" in type(exc).__name__:
        return AgentServiceError(
            "Missing environment variable.",
            hint="Copy .env.example to .env and fill in all required keys.",
        )

    return AgentServiceError(f"Agent error: {message}")
