import os

import resend
from langchain_core.tools import tool
from resend.exceptions import ResendError

from agent.config import get_email_recipients
from agent.errors import friendly_agent_error


def _resolve_recipients(extra: str = "") -> list[str]:
    recipients = list(get_email_recipients())
    if extra:
        for email in extra.split(","):
            email = email.strip()
            if email and email.lower() not in {r.lower() for r in recipients}:
                recipients.append(email)
    return recipients


@tool
def send_email(subject: str, body: str, recipients: str = "") -> str:
    """Send email summary. Optional extra recipients as comma-separated emails."""
    try:
        to_list = _resolve_recipients(recipients)
        if not to_list:
            return "Error: no recipient configured. Set RESEND_TO_EMAIL in .env."

        resend.api_key = os.environ["RESEND_API_KEY"]
        payload = {
            "from": os.environ["RESEND_FROM_EMAIL"],
            "to": to_list,
            "subject": subject,
        }
        if "<" in body and ">" in body:
            payload["html"] = body
        else:
            payload["text"] = body

        response = resend.Emails.send(payload)
        joined = ", ".join(to_list)
        return f"Email sent successfully to {joined} (id: {response['id']})."
    except ResendError as exc:
        raise friendly_agent_error(exc) from exc


def get_email_tool():
    return send_email
