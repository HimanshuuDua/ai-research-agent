import os

from dotenv import load_dotenv

load_dotenv()

PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")

RESEND_TEST_FROM = "onboarding@resend.dev"

BASE_REQUIRED_ENV_KEYS = [
    "GOOGLE_API_KEY",
    "SERPAPI_API_KEY",
]

RESEND_REQUIRED_ENV_KEYS = [
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
]

SMTP_REQUIRED_ENV_KEYS = [
    "SMTP_USER",
    "SMTP_PASSWORD",
]


def get_email_provider() -> str:
    explicit = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    if explicit in {"smtp", "resend"}:
        return explicit
    if os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"):
        return "smtp"
    return "resend"


def get_missing_env_keys() -> list[str]:
    missing = [key for key in BASE_REQUIRED_ENV_KEYS if not os.getenv(key)]

    if get_email_provider() == "smtp":
        missing.extend(key for key in SMTP_REQUIRED_ENV_KEYS if not os.getenv(key))
    else:
        missing.extend(key for key in RESEND_REQUIRED_ENV_KEYS if not os.getenv(key))

    if not get_email_recipients():
        missing.append("RESEND_TO_EMAIL")

    return missing


def get_email_recipients() -> list[str]:
    """Parse RESEND_TO_EMAIL — supports comma-separated multiple addresses."""
    raw = os.getenv("RESEND_TO_EMAIL", "")
    return [email.strip() for email in raw.split(",") if email.strip()]


def is_resend_test_mode() -> bool:
    if get_email_provider() == "smtp":
        return False
    from_email = os.getenv("RESEND_FROM_EMAIL", "").strip().lower()
    return RESEND_TEST_FROM in from_email


def get_resend_account_email() -> str:
    """Email allowed to receive when using Resend's test sender."""
    explicit = os.getenv("RESEND_ACCOUNT_EMAIL", "").strip()
    if explicit:
        return explicit
    recipients = get_email_recipients()
    return recipients[0] if recipients else ""


def validate_outbound_recipients(recipients: list[str]) -> str | None:
    """Return an error message when a send should be blocked, else None."""
    if not recipients:
        return "No recipient configured. Add an email in the UI or set RESEND_TO_EMAIL."

    if get_email_provider() == "smtp":
        return None

    if not is_resend_test_mode():
        return None

    allowed = get_resend_account_email().lower()
    if not allowed:
        return (
            "Set RESEND_ACCOUNT_EMAIL to the email you used to sign up at resend.com. "
            "The test sender onboarding@resend.dev can only deliver to that address."
        )

    blocked = [email for email in recipients if email.lower() != allowed]
    if not blocked:
        return None

    return (
        f"Cannot send to {', '.join(blocked)} while RESEND_FROM_EMAIL is "
        f"{RESEND_TEST_FROM}. Resend's test sender only delivers to {allowed}. "
        "Switch to Gmail SMTP instead: set EMAIL_PROVIDER=smtp, SMTP_USER, and "
        "SMTP_PASSWORD (Google App Password) in .env — no domain verification needed."
    )


def get_email_delivery_info() -> dict:
    provider = get_email_provider()
    info = {
        "provider": provider,
        "default_recipients": get_email_recipients(),
    }

    if provider == "smtp":
        info.update(
            {
                "mode": "smtp",
                "from_email": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER", ""),
                "hint": "Gmail SMTP active — you can send to any email address.",
            }
        )
        return info

    test_mode = is_resend_test_mode()
    info.update(
        {
            "mode": "test" if test_mode else "production",
            "from_email": os.getenv("RESEND_FROM_EMAIL", ""),
        }
    )
    if test_mode:
        info["test_recipient_only"] = get_resend_account_email()
        info["hint"] = (
            "Resend test mode: only your account email can receive. "
            "Use EMAIL_PROVIDER=smtp with a Gmail App Password to email anyone."
        )
    else:
        info["hint"] = "Resend production mode: multiple recipients supported."
    return info
