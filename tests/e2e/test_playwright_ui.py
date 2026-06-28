import json
import urllib.request

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_health_endpoint(live_server: str):
    with urllib.request.urlopen(f"{live_server}/api/health", timeout=10) as response:
        data = json.loads(response.read().decode())
    assert data["status"] == "ok"
    assert "email_delivery" in data
    assert data["email_delivery"]["mode"] in {"test", "production", "smtp", "brevo"}


def test_homepage_loads(page: Page, live_server: str):
    page.goto(live_server)
    expect(page.locator("h1")).to_have_text("AI Research Agent")
    expect(page.locator("#prompt")).to_be_visible()
    expect(page.locator("#send")).to_be_visible()
    expect(page.locator("#mode")).to_be_visible()
    expect(page.locator("#chat-main")).to_be_visible()
    expect(page.locator("#recipient-add")).to_be_visible()
    expect(page.locator("#recipient-add-btn")).to_be_visible()


def test_add_recipient_email(page: Page, live_server: str):
    page.goto(live_server)
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'"
    )
    page.fill("#recipient-add", "friend@example.com")
    page.click("#recipient-add-btn")
    chip = page.locator("#recipient-list .recipient-chip", has_text="friend@example.com")
    expect(chip).to_be_visible()


def test_email_test_mode_hint(page: Page, live_server: str):
    page.goto(live_server)
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'"
    )
    hint = page.locator("#email-mode-hint")
    expect(hint).to_be_visible()
    text = hint.inner_text().lower()
    assert "smtp" in text or "test mode" in text or "recipients" in text


def test_document_drop_attaches_without_auto_send(page: Page, live_server: str, tmp_path):
    page.goto(live_server)
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'"
    )

    doc_path = tmp_path / "sample.txt"
    doc_path.write_text("Playwright test document content.", encoding="utf-8")

    page.evaluate(
        """async ([selector, name, content]) => {
            const target = document.querySelector(selector);
            const file = new File([content], name, { type: "text/plain" });
            const dt = new DataTransfer();
            dt.items.add(file);
            const event = new DragEvent("drop", { dataTransfer: dt, bubbles: true });
            target.dispatchEvent(event);
        }""",
        ["#chat-main", "sample.txt", doc_path.read_text(encoding="utf-8")],
    )

    page.wait_for_function(
        "() => document.querySelectorAll('.pending-doc').length > 0",
        timeout=15000,
    )
    expect(page.locator(".pending-doc")).to_contain_text("sample.txt")
    expect(page.locator(".message-row.assistant")).to_have_count(0)
    expect(page.locator(".message-row.user")).to_have_count(0)
