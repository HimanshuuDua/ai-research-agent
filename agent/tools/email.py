import os

import resend
from langchain_core.tools import tool
from resend.exceptions import ResendError

from agent.errors import friendly_agent_error


@tool
def send_email(subject: str, body: str) -> str:
    """Send an email summary to the user. Use this last to deliver final results."""
    try:
        resend.api_key = os.environ["RESEND_API_KEY"]
        payload = {
            "from": os.environ["RESEND_FROM_EMAIL"],
            "to": [os.environ["RESEND_TO_EMAIL"]],
            "subject": subject,
        }
        if "<" in body and ">" in body:
            payload["html"] = body
        else:
            payload["text"] = body

        response = resend.Emails.send(payload)
        return f"Email sent successfully to {os.environ['RESEND_TO_EMAIL']} (id: {response['id']})."
    except ResendError as exc:
        raise friendly_agent_error(exc) from exc


def get_email_tool():
    return send_email
