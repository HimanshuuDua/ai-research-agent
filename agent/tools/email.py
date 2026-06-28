from langchain_core.tools import tool

from agent.config import get_valid_email_recipients, validate_outbound_recipients
from agent.context import get_active_recipients
from agent.email_delivery import deliver_email
from agent.errors import AgentServiceError, friendly_agent_error


def _resolve_recipients(extra: str = "") -> list[str]:
    session = get_active_recipients()
    recipients = list(session) if session else list(get_valid_email_recipients())

    if extra:
        for email in extra.split(","):
            email = email.strip()
            if email and email.lower() not in {r.lower() for r in recipients}:
                recipients.append(email)
    return recipients


@tool
def send_email(subject: str, body: str, recipients: str = "") -> str:
    """Send email summary. recipients: comma-separated addresses (any inbox when Gmail SMTP is active)."""
    to_list = _resolve_recipients(recipients)
    if validation_error := validate_outbound_recipients(to_list):
        return f"Error: {validation_error}"

    try:
        return deliver_email(to_list, subject, body)
    except AgentServiceError as exc:
        detail = str(exc)
        if exc.hint:
            detail = f"{detail} Hint: {exc.hint}"
        return f"Error: {detail}"
    except Exception as exc:
        err = friendly_agent_error(exc)
        detail = str(err)
        if err.hint:
            detail = f"{detail} Hint: {err.hint}"
        return f"Error: {detail}"


def get_email_tool():
    return send_email
