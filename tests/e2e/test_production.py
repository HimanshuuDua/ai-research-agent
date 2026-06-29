"""Live Playwright tests against the Vercel deployment.

Run: E2E_PRODUCTION=1 pytest tests/e2e/test_production.py -v
"""

import json
import os
import re
import time
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


def _fetch_json(path: str, timeout: int = 20) -> dict:
    with urllib.request.urlopen(f"{PRODUCTION_URL}{path}", timeout=timeout) as response:
        return json.loads(response.read().decode())


@pytest.fixture(scope="session")
def production_url() -> str:
    return PRODUCTION_URL


def test_production_health(production_url: str):
    started = time.time()
    data = _fetch_json("/api/health")
    elapsed = time.time() - started

    assert elapsed < 8, f"Health check took {elapsed:.1f}s (expected < 8s)"
    assert data["status"] == "ok"
    assert "email_delivery" in data
    delivery = data["email_delivery"]
    assert delivery["mode"] in {"test", "production", "smtp", "brevo"}
    assert "email_recipients" not in data
    assert data.get("gemini_key_count", 0) >= 1
    assert "email_account_count" in data

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
    page.goto(production_url, wait_until="domcontentloaded")
    expect(page.locator("h1")).to_have_text("AI Research Agent")
    expect(page.locator("#prompt")).to_be_visible()
    expect(page.locator("#recipient-add")).to_be_visible()
    page.wait_for_function(
        "() => ['API ready', 'Missing env vars'].includes("
        "document.querySelector('#status .label')?.textContent)",
        timeout=15000,
    )


def test_production_email_hint(page: Page, production_url: str):
    page.goto(production_url, wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'",
        timeout=15000,
    )
    hint = page.locator("#email-mode-hint")
    expect(hint).to_be_visible()
    text = hint.inner_text().lower()
    assert "recipients" in text or "test mode" in text


def test_production_recipient_chips(page: Page, production_url: str):
    page.goto(production_url, wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'",
        timeout=15000,
    )
    page.fill("#recipient-add", "qa-check@example.com")
    page.click("#recipient-add-btn")
    chip = page.locator("#recipient-list .recipient-chip", has_text="qa-check@example.com")
    expect(chip).to_be_visible()


def test_production_search_only_chat(page: Page, production_url: str):
    """Live end-to-end: send a quick search prompt and wait for assistant reply."""
    page.set_default_timeout(120_000)
    page.goto(production_url, wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'",
        timeout=15000,
    )

    page.select_option("#mode", "search_only")
    page.fill(
        "#prompt",
        "List 3 AI agent trends in 2025 in 3 short bullet points. One web search only.",
    )
    started = time.time()
    page.click("#send")

    page.wait_for_selector(
        ".message-row.assistant .bubble, .message-row.system .bubble",
        timeout=120_000,
    )
    elapsed = time.time() - started

    if page.locator(".message-row.system .bubble").count():
        system_text = page.locator(".message-row.system .bubble").last.inner_text().lower()
        if "quota" in system_text:
            pytest.skip("Gemini API quota exceeded on production — retry later or set GEMINI_MODEL=gemini-2.5-flash-lite on Vercel")
        pytest.fail(f"Chat returned an error instead of a reply: {system_text[:200]}")

    assistant_text = page.locator(".message-row.assistant .bubble").last.inner_text()
    assert len(assistant_text.strip()) > 20, "Assistant reply was empty"
    assert elapsed < 120, f"Chat took {elapsed:.0f}s (expected < 120s on live site)"


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
