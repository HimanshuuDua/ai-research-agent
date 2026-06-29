import os
import re

from dotenv import load_dotenv

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

load_dotenv()

_DEFAULT_PRIMARY = "gemini-2.5-flash-lite" if os.getenv("VERCEL") else "gemini-2.5-flash"
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", _DEFAULT_PRIMARY)
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

BREVO_REQUIRED_ENV_KEYS = [
    "BREVO_API_KEY",
]


def get_email_provider() -> str:
    explicit = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    has_smtp = bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))

    if explicit == "brevo":
        return "brevo"
    if explicit == "smtp":
        return "smtp"
    if os.getenv("BREVO_API_KEY") and not has_smtp:
        return "brevo"
    if has_smtp:
        return "smtp"
    if explicit == "resend":
        return "resend"
    return "resend"


def get_missing_env_keys() -> list[str]:
    missing = [key for key in BASE_REQUIRED_ENV_KEYS if not os.getenv(key)]

    if get_email_provider() == "smtp":
        missing.extend(key for key in SMTP_REQUIRED_ENV_KEYS if not os.getenv(key))
    elif get_email_provider() == "brevo":
        missing.extend(key for key in BREVO_REQUIRED_ENV_KEYS if not os.getenv(key))
        if not os.getenv("BREVO_FROM_EMAIL") and not os.getenv("SMTP_USER"):
            missing.append("BREVO_FROM_EMAIL")
    else:
        missing.extend(key for key in RESEND_REQUIRED_ENV_KEYS if not os.getenv(key))

    if not get_valid_email_recipients():
        missing.append("RESEND_TO_EMAIL")

    return missing


def get_agent_max_iterations() -> int:
    default = "5" if os.getenv("VERCEL") else "7"
    return int(os.getenv("AGENT_MAX_ITERATIONS", default))


def get_agent_max_execution_time() -> int | None:
    if os.getenv("AGENT_MAX_EXECUTION_TIME"):
        return int(os.getenv("AGENT_MAX_EXECUTION_TIME"))
    return 25 if os.getenv("VERCEL") else 90


def is_valid_email(address: str) -> bool:
    return bool(EMAIL_PATTERN.match(address.strip()))


def get_email_recipients() -> list[str]:
    """Parse RESEND_TO_EMAIL — supports comma-separated multiple addresses."""
    raw = os.getenv("RESEND_TO_EMAIL", "")
    return [email.strip() for email in raw.split(",") if email.strip()]


def get_valid_email_recipients() -> list[str]:
    return [email for email in get_email_recipients() if is_valid_email(email)]


def get_email_config_warnings() -> list[dict[str, str]]:
    """Surface misconfiguration (e.g. RESEND_TO_EMAIL=smtp on Vercel)."""
    warnings: list[dict[str, str]] = []
    provider = get_email_provider()
    recipients = get_email_recipients()

    invalid = [email for email in recipients if not is_valid_email(email)]
    if invalid:
        warnings.append(
            {
                "code": "invalid_recipients",
                "message": (
                    f"RESEND_TO_EMAIL contains invalid addresses: {', '.join(invalid)}. "
                    "Use real emails like you@gmail.com, not provider names."
                ),
            }
        )

    if provider == "smtp":
        if not os.getenv("SMTP_USER"):
            warnings.append(
                {
                    "code": "smtp_missing_user",
                    "message": "EMAIL_PROVIDER is smtp but SMTP_USER is not set.",
                }
            )
        elif not is_valid_email(os.getenv("SMTP_USER", "")):
            warnings.append(
                {
                    "code": "smtp_invalid_user",
                    "message": "SMTP_USER must be a valid Gmail address.",
                }
            )
        if not os.getenv("SMTP_PASSWORD"):
            warnings.append(
                {
                    "code": "smtp_missing_password",
                    "message": "EMAIL_PROVIDER is smtp but SMTP_PASSWORD is not set.",
                }
            )
    elif provider == "resend" and is_resend_test_mode():
        allowed = get_resend_account_email()
        if allowed and not is_valid_email(allowed):
            warnings.append(
                {
                    "code": "invalid_account_email",
                    "message": "RESEND_ACCOUNT_EMAIL is not a valid email address.",
                }
            )

    return warnings


def is_resend_test_mode() -> bool:
    if get_email_provider() in {"smtp", "brevo"}:
        return False
    from_email = os.getenv("RESEND_FROM_EMAIL", "").strip().lower()
    return RESEND_TEST_FROM in from_email


def get_resend_account_email() -> str:
    """Email allowed to receive when using Resend's test sender."""
    explicit = os.getenv("RESEND_ACCOUNT_EMAIL", "").strip()
    if explicit and is_valid_email(explicit):
        return explicit
    for email in get_email_recipients():
        if is_valid_email(email):
            return email
    return ""


def validate_outbound_recipients(recipients: list[str]) -> str | None:
    """Return an error message when a send should be blocked, else None."""
    if not recipients:
        return "No recipient configured. Add an email in the UI or set RESEND_TO_EMAIL."

    invalid = [email for email in recipients if not is_valid_email(email)]
    if invalid:
        return f"Invalid email address: {', '.join(invalid)}"

    if get_email_provider() in {"smtp", "brevo"}:
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
        "default_recipients": get_valid_email_recipients(),
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

    if provider == "brevo":
        info.update(
            {
                "mode": "brevo",
                "from_email": os.getenv("BREVO_FROM_EMAIL") or os.getenv("SMTP_USER", ""),
                "hint": "Brevo API active — send to any email (works on Vercel).",
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
