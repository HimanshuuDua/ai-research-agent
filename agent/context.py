from contextvars import ContextVar

_active_recipients: ContextVar[list[str] | None] = ContextVar("active_recipients", default=None)
_active_documents: ContextVar[list[dict] | None] = ContextVar("active_documents", default=None)


def set_active_recipients(recipients: list[str] | None) -> None:
    _active_recipients.set(recipients)


def get_active_recipients() -> list[str] | None:
    return _active_recipients.get()


def set_active_documents(documents: list[dict] | None) -> None:
    _active_documents.set(documents)


def get_active_documents() -> list[dict] | None:
    return _active_documents.get()


def parse_recipient_string(raw: str) -> list[str]:
    return [email.strip() for email in raw.split(",") if email.strip()]
