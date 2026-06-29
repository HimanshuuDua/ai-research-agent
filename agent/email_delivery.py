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
from agent.key_pool import get_brevo_api_keys, get_resend_api_keys, get_smtp_accounts
from agent.errors import AgentServiceError, friendly_agent_error


def _is_html_body(body: str) -> bool:
    return "<" in body and ">" in body


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


def _is_retryable_email_error(exc: Exception) -> bool:
    text = str(exc).lower()
    if any(
        phrase in text
        for phrase in (
            "quota",
            "limit",
            "daily",
            "exceeded",
            "too many",
            "rate",
            "429",
            "452",
            "454",
            "550 5.4.5",
            "421",
        )
    ):
        return True
    if isinstance(exc, smtplib.SMTPResponseException):
        return exc.smtp_code in {421, 450, 452, 454, 550, 552}
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in {429, 402, 403}
    if isinstance(exc, ResendError):
        return "rate" in text or "limit" in text or "429" in text
    return isinstance(exc, (smtplib.SMTPAuthenticationError, OSError))


def verify_smtp_login() -> dict:
    """Verify Gmail SMTP login without sending mail."""
    accounts = get_smtp_accounts()
    if not accounts:
        return {"ok": False, "error": "No SMTP accounts configured.", "hint": "Set SMTP_USER and SMTP_PASSWORD."}

    account = accounts[0]
    host = account["host"]
    port = int(account["port"])
    try:
        server = _smtp_connect(host, port, account["user"], account["password"])
        server.quit()
        return {
            "ok": True,
            "host": host,
            "port": port,
            "account_count": len(accounts),
        }
    except Exception as exc:
        err = friendly_agent_error(exc)
        hint = err.hint or ""
        if os.getenv("VERCEL"):
            hint = (
                f"{hint} Gmail SMTP often fails on Vercel. "
                "Set EMAIL_PROVIDER=brevo with a free Brevo API key for production."
            ).strip()
        return {"ok": False, "error": str(err), "hint": hint, "host": host, "port": port}


def send_via_smtp(
    to_list: list[str],
    subject: str,
    body: str,
    *,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    from_header: str | None = None,
) -> str:
    account = get_smtp_accounts()[0]
    host = host or account["host"]
    port = port or int(account["port"])
    user = user or account["user"]
    password = password or account["password"]
    from_header = from_header or account["from_header"]
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

    server = _smtp_connect(host, port, user, password)
    try:
        server.sendmail(from_email, to_list, message.as_string())
    finally:
        server.quit()

    return ", ".join(to_list)


def send_via_brevo(to_list: list[str], subject: str, body: str, api_key: str | None = None) -> str:
    key = api_key or os.environ["BREVO_API_KEY"]
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
            "api-key": key,
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


def send_via_resend(to_list: list[str], subject: str, body: str, api_key: str | None = None) -> str:
    resend.api_key = api_key or os.environ["RESEND_API_KEY"]
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
    last_error: Exception | None = None

    if provider == "smtp":
        accounts = get_smtp_accounts()
        if not accounts:
            raise AgentServiceError("No SMTP accounts configured.")
        for account in accounts:
            try:
                send_via_smtp(
                    to_list,
                    subject,
                    body,
                    host=account["host"],
                    port=int(account["port"]),
                    user=account["user"],
                    password=account["password"],
                    from_header=account["from_header"],
                )
                suffix = f" via SMTP ({account['user']})" if len(accounts) > 1 else " via SMTP"
                return f"Email sent successfully to {joined}{suffix}."
            except Exception as exc:
                last_error = exc
                if _is_retryable_email_error(exc):
                    continue
                raise friendly_agent_error(exc) from exc
        raise friendly_agent_error(
            last_error or AgentServiceError("SMTP delivery failed after trying all configured accounts.")
        )

    if provider == "brevo":
        keys = get_brevo_api_keys()
        for key in keys:
            try:
                message_id = send_via_brevo(to_list, subject, body, api_key=key)
                return f"Email sent successfully to {joined} via Brevo (id: {message_id})."
            except AgentServiceError as exc:
                last_error = exc
                if _is_retryable_email_error(exc):
                    continue
                raise
        raise last_error or AgentServiceError("Brevo email delivery failed.")

    keys = get_resend_api_keys()
    for key in keys:
        try:
            message_id = send_via_resend(to_list, subject, body, api_key=key)
            return f"Email sent successfully to {joined} (id: {message_id})."
        except ResendError as exc:
            last_error = exc
            if _is_retryable_email_error(exc):
                continue
            raise friendly_agent_error(exc) from exc
    raise friendly_agent_error(
        last_error or AgentServiceError("Email delivery failed after trying all configured keys.")
    )


def get_email_pool_size() -> int:
    provider = get_email_provider()
    if provider == "smtp":
        return len(get_smtp_accounts())
    if provider == "brevo":
        return len(get_brevo_api_keys())
    return len(get_resend_api_keys())
