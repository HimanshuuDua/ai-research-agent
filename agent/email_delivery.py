import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

import resend
from resend.exceptions import ResendError

from agent.config import get_email_provider
from agent.errors import friendly_agent_error


def _is_html_body(body: str) -> bool:
    return "<" in body and ">" in body


def send_via_smtp(to_list: list[str], subject: str, body: str) -> str:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    from_header = os.getenv("SMTP_FROM") or user
    _, from_email = parseaddr(from_header)
    if not from_email:
        from_email = user

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_header
    message["To"] = ", ".join(to_list)

    if _is_html_body(body):
        message.attach(MIMEText(body, "html"))
    else:
        message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_email, to_list, message.as_string())

    return ", ".join(to_list)


def send_via_resend(to_list: list[str], subject: str, body: str) -> str:
    resend.api_key = os.environ["RESEND_API_KEY"]
    payload = {
        "from": os.environ["RESEND_FROM_EMAIL"],
        "to": to_list,
        "subject": subject,
    }
    if _is_html_body(body):
        payload["html"] = body
    else:
        payload["text"] = body

    response = resend.Emails.send(payload)
    return response["id"]


def deliver_email(to_list: list[str], subject: str, body: str) -> str:
    provider = get_email_provider()
    joined = ", ".join(to_list)

    if provider == "smtp":
        try:
            send_via_smtp(to_list, subject, body)
            return f"Email sent successfully to {joined} via SMTP."
        except smtplib.SMTPException as exc:
            raise friendly_agent_error(exc) from exc

    try:
        message_id = send_via_resend(to_list, subject, body)
        return f"Email sent successfully to {joined} (id: {message_id})."
    except ResendError as exc:
        raise friendly_agent_error(exc) from exc
