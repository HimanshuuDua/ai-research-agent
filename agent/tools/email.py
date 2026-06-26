import os

import resend
from langchain_core.tools import tool


@tool
def send_email(subject: str, body: str) -> str:
    """Send an email summary to the user. Use this last to deliver final results."""
    resend.api_key = os.environ["RESEND_API_KEY"]

    response = resend.Emails.send(
        {
            "from": os.environ["RESEND_FROM_EMAIL"],
            "to": [os.environ["RESEND_TO_EMAIL"]],
            "subject": subject,
            "text": body,
        }
    )

    return f"Email sent successfully to {os.environ['RESEND_TO_EMAIL']} (id: {response['id']})."


def get_email_tool():
    return send_email