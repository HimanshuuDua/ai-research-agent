import json
import os
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

import resend
from resend.exceptions import ResendError

from agent.config import get_email_provider
from agent.errors import AgentServiceError, friendly_agent_error


def _is_html_body(body: str) -> bool:
    return "<" in body and ">" in body


def _smtp_password() -> str:
    return os.environ["SMTP_PASSWORD"].replace(" ", "")


def _smtp_use_ssl(port: int) -> bool:
    if port == 465:
        return True
    return os.getenv("SMTP_USE_SSL", "").strip().lower() in {"1", "true", "yes"}


def _smtp_connect(host: str, port: int, user: str, password: str) -> smtplib.SMTP:
    if _smtp_use_ssl(port):
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls()
    server.login(user, password)
    return server


def verify_smtp_login() -> dict:
    """Verify Gmail SMTP login without sending mail."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = _smtp_password()
    try:
        server = _smtp_connect(host, port, user, password)
        server.quit()
        return {"ok": True, "host": host, "port": port}
    except Exception as exc:
        err = friendly_agent_error(exc)
        hint = err.hint or ""
        if os.getenv("VERCEL"):
            hint = (
                f"{hint} Gmail SMTP often fails on Vercel. "
                "Set EMAIL_PROVIDER=brevo with a free Brevo API key for production."
            ).strip()
        return {"ok": False, "error": str(err), "hint": hint, "host": host, "port": port}


def send_via_smtp(to_list: list[str], subject: str, body: str) -> str:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = _smtp_password()
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

    try:
        server = _smtp_connect(host, port, user, password)
        server.sendmail(from_email, to_list, message.as_string())
        server.quit()
    except smtplib.SMTPException as exc:
        raise friendly_agent_error(exc) from exc
    except OSError as exc:
        raise friendly_agent_error(exc) from exc

    return ", ".join(to_list)


def send_via_brevo(to_list: list[str], subject: str, body: str) -> str:
    api_key = os.environ["BREVO_API_KEY"]
    from_email = os.getenv("BREVO_FROM_EMAIL") or os.getenv("SMTP_USER", "")
    from_name = os.getenv("BREVO_FROM_NAME", "AI Research Agent")

    payload = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": email} for email in to_list],
        "subject": subject,
    }
    if _is_html_body(body):
        payload["htmlContent"] = body
    else:
        payload["textContent"] = body

    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode(),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise AgentServiceError(
            f"Brevo email delivery failed ({exc.code}).",
            hint=f"Check BREVO_API_KEY and verify sender {from_email} in Brevo dashboard. {detail[:200]}",
        ) from exc

    message_id = result.get("messageId", "ok")
    return str(message_id)


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
        send_via_smtp(to_list, subject, body)
        return f"Email sent successfully to {joined} via SMTP."

    if provider == "brevo":
        message_id = send_via_brevo(to_list, subject, body)
        return f"Email sent successfully to {joined} via Brevo (id: {message_id})."

    try:
        message_id = send_via_resend(to_list, subject, body)
        return f"Email sent successfully to {joined} (id: {message_id})."
    except ResendError as exc:
        raise friendly_agent_error(exc) from exc
