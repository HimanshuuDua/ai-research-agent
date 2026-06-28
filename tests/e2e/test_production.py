"""Smoke tests against the live Vercel deployment.

Run: E2E_BASE_URL=https://your-app.vercel.app pytest tests/e2e/test_production.py -q
"""

import json
import os
import re
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.production]

PRODUCTION_URL = os.getenv(
    "E2E_BASE_URL",
    "https://ai-research-agent-ecru-zeta.vercel.app",
).rstrip("/")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@pytest.fixture(scope="session", autouse=True)
def require_production_flag():
    if not os.getenv("E2E_PRODUCTION"):
        pytest.skip("Set E2E_PRODUCTION=1 to run live deployment tests")


def _fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{PRODUCTION_URL}{path}", timeout=20) as response:
        return json.loads(response.read().decode())


@pytest.fixture(scope="session")
def production_url() -> str:
    return PRODUCTION_URL


def test_production_health(production_url: str):
    data = _fetch_json("/api/health")
    assert data["status"] == "ok"
    assert "email_delivery" in data
    delivery = data["email_delivery"]
    assert delivery["mode"] in {"test", "production", "smtp", "brevo"}

    for email in data.get("email_recipients", []):
        assert EMAIL_RE.match(email), f"Invalid default recipient on server: {email!r}"

    if delivery["mode"] == "smtp":
        assert delivery.get("provider") == "smtp"
        ping = _fetch_json("/api/email/ping")
        if not ping.get("ok"):
            pytest.fail(f"SMTP login failed on production: {ping.get('error')} — {ping.get('hint')}")
    if data.get("config_warnings"):
        pytest.fail(
            "Production config warnings: "
            + "; ".join(w["message"] for w in data["config_warnings"])
        )


def test_production_homepage(page: Page, production_url: str):
    page.goto(production_url)
    expect(page.locator("h1")).to_have_text("AI Research Agent")
    expect(page.locator("#prompt")).to_be_visible()
    expect(page.locator("#recipient-add")).to_be_visible()
    page.wait_for_function(
        "() => ['API ready', 'Missing env vars'].includes("
        "document.querySelector('#status .label')?.textContent)"
    )


def test_production_recipient_chips(page: Page, production_url: str):
    page.goto(production_url)
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'"
    )
    page.fill("#recipient-add", "qa-check@example.com")
    page.click("#recipient-add-btn")
    chip = page.locator("#recipient-list .recipient-chip", has_text="qa-check@example.com")
    expect(chip).to_be_visible()


def test_production_upload_rejects_empty(production_url: str):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename=""\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
        f"\r\n--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        f"{production_url}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=20)
    assert exc.value.code == 400


def test_production_chat_rejects_invalid_mode(production_url: str):
    payload = json.dumps({"prompt": "hello", "mode": "hack"}).encode()
    req = urllib.request.Request(
        f"{production_url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=20)
    assert exc.value.code == 400
