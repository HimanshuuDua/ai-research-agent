"""Rotate multiple API keys when quota limits are hit."""

import os


def _split_keys(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def get_google_api_keys() -> list[str]:
    multi = os.getenv("GOOGLE_API_KEYS", "")
    if multi.strip():
        keys = _split_keys(multi)
        if keys:
            return keys
    single = os.getenv("GOOGLE_API_KEY", "").strip()
    return [single] if single else []


def get_brevo_api_keys() -> list[str]:
    multi = os.getenv("BREVO_API_KEYS", "")
    if multi.strip():
        keys = _split_keys(multi)
        if keys:
            return keys
    single = os.getenv("BREVO_API_KEY", "").strip()
    return [single] if single else []


def get_resend_api_keys() -> list[str]:
    multi = os.getenv("RESEND_API_KEYS", "")
    if multi.strip():
        keys = _split_keys(multi)
        if keys:
            return keys
    single = os.getenv("RESEND_API_KEY", "").strip()
    return [single] if single else []
