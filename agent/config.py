import os

from dotenv import load_dotenv

load_dotenv()

PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")

RESEND_TEST_FROM = "onboarding@resend.dev"

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


def is_resend_test_mode() -> bool:
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
        "To email anyone: verify your domain at https://resend.com/domains, then set "
        "RESEND_FROM_EMAIL=Your Name <notify@yourdomain.com> in .env and Vercel."
    )


def get_email_delivery_info() -> dict:
    test_mode = is_resend_test_mode()
    info = {
        "mode": "test" if test_mode else "production",
        "from_email": os.getenv("RESEND_FROM_EMAIL", ""),
        "default_recipients": get_email_recipients(),
    }
    if test_mode:
        info["test_recipient_only"] = get_resend_account_email()
        info["hint"] = (
            "Test mode: only your Resend account email can receive mail. "
            "Verify a domain to send to any address."
        )
    else:
        info["hint"] = "Production mode: multiple recipients are supported."
    return info
