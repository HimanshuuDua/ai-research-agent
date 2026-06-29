"""Rotate multiple API keys and SMTP accounts when limits are hit."""

import os
from typing import TypedDict


class SmtpAccount(TypedDict):
    host: str
    port: str
    user: str
    password: str
    from_header: str


def _split_keys(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _split_api_keys(multi_var: str, single_var: str) -> list[str]:
    multi = os.getenv(multi_var, "")
    if multi.strip():
        keys = _split_keys(multi)
        if keys:
            return keys
    single = os.getenv(single_var, "").strip()
    if not single:
        return []
    if "," in single:
        return _split_keys(single)
    return [single]


def get_google_api_keys() -> list[str]:
    return _split_api_keys("GOOGLE_API_KEYS", "GOOGLE_API_KEY")


def get_brevo_api_keys() -> list[str]:
    return _split_api_keys("BREVO_API_KEYS", "BREVO_API_KEY")


def get_resend_api_keys() -> list[str]:
    return _split_api_keys("RESEND_API_KEYS", "RESEND_API_KEY")


def get_smtp_accounts() -> list[SmtpAccount]:
    """SMTP accounts for rotation — single or comma-separated multi-account."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = os.getenv("SMTP_PORT", "587")

    users_raw = os.getenv("SMTP_USERS", "").strip() or os.getenv("SMTP_USER", "").strip()
    passwords_raw = os.getenv("SMTP_PASSWORDS", "").strip() or os.getenv("SMTP_PASSWORD", "").strip()
    froms_raw = os.getenv("SMTP_FROMS", "").strip() or os.getenv("SMTP_FROM", "").strip()

    if not users_raw or not passwords_raw:
        return []

    users = _split_keys(users_raw) if "," in users_raw else [users_raw]
    passwords = (
        [_normalize_smtp_password(p) for p in _split_keys(passwords_raw)]
        if "," in passwords_raw
        else [_normalize_smtp_password(passwords_raw)]
    )
    froms = _split_keys(froms_raw) if froms_raw and "," in froms_raw else ([froms_raw] if froms_raw else [])

    if len(users) != len(passwords):
        # Misconfigured — fall back to first pair only to avoid leaking wrong combos.
        users = users[:1]
        passwords = passwords[:1]

    accounts: list[SmtpAccount] = []
    for index, (user, password) in enumerate(zip(users, passwords)):
        from_header = froms[index] if index < len(froms) else user
        accounts.append(
            {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "from_header": from_header,
            }
        )
    return accounts


def _normalize_smtp_password(password: str) -> str:
    return password.replace(" ", "")
