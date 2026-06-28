from langchain_core.tools import tool

from agent.config import get_email_recipients, validate_outbound_recipients
from agent.context import get_active_recipients
from agent.email_delivery import deliver_email


def _resolve_recipients(extra: str = "") -> list[str]:
    session = get_active_recipients()
    recipients = list(session) if session else list(get_email_recipients())

    if extra:
        for email in extra.split(","):
            email = email.strip()
            if email and email.lower() not in {r.lower() for r in recipients}:
                recipients.append(email)
    return recipients


@tool
def send_email(subject: str, body: str, recipients: str = "") -> str:
    """Send email summary. Use recipients for comma-separated addresses from the user."""
    to_list = _resolve_recipients(recipients)
    if validation_error := validate_outbound_recipients(to_list):
        return f"Error: {validation_error}"

    return deliver_email(to_list, subject, body)


def get_email_tool():
    return send_email
