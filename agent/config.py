import os

from dotenv import load_dotenv

load_dotenv()

PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")

REQUIRED_ENV_KEYS = [
    "GOOGLE_API_KEY",
    "SERPAPI_API_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "RESEND_TO_EMAIL",
]


def get_missing_env_keys() -> list[str]:
    return [key for key in REQUIRED_ENV_KEYS if not os.getenv(key)]


def get_email_recipients() -> list[str]:
    """Parse RESEND_TO_EMAIL — supports comma-separated multiple addresses."""
    raw = os.getenv("RESEND_TO_EMAIL", "")
    return [email.strip() for email in raw.split(",") if email.strip()]
