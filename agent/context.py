from contextvars import ContextVar

_active_recipients: ContextVar[list[str] | None] = ContextVar("active_recipients", default=None)


def set_active_recipients(recipients: list[str] | None) -> None:
    _active_recipients.set(recipients)


def get_active_recipients() -> list[str] | None:
    return _active_recipients.get()


def parse_recipient_string(raw: str) -> list[str]:
    return [email.strip() for email in raw.split(",") if email.strip()]
