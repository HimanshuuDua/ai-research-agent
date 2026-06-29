"""Mobile viewport UI/UX tests (Playwright)."""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

IPHONE_VIEWPORT = {"width": 390, "height": 844}


@pytest.fixture
def mobile_page(page: Page, live_server: str):
    page.set_viewport_size(IPHONE_VIEWPORT)
    page.goto(live_server, wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelector('#status .label')?.textContent === 'API ready'",
        timeout=15000,
    )
    return page


def test_mobile_chat_and_composer_visible(mobile_page: Page):
    expect(mobile_page.locator("#chat-main")).to_be_visible()
    expect(mobile_page.locator("#prompt")).to_be_visible()
    expect(mobile_page.locator("#send")).to_be_visible()

    prompt_box = mobile_page.locator("#prompt").bounding_box()
    send_box = mobile_page.locator("#send").bounding_box()
    assert prompt_box and send_box
    assert send_box["width"] >= 44
    assert send_box["height"] >= 44


def test_mobile_settings_drawer(mobile_page: Page):
    toggle = mobile_page.locator("#settings-toggle")
    sidebar = mobile_page.locator("#sidebar")
    backdrop = mobile_page.locator("#settings-backdrop")

    expect(toggle).to_be_visible()

    toggle.click()
    expect(sidebar).to_have_class(re.compile(r"mobile-open"))
    expect(backdrop).to_have_class(re.compile(r"visible"))
    expect(mobile_page.locator("#mode")).to_be_visible()
    expect(mobile_page.locator("#recipient-add")).to_be_visible()

    mobile_page.locator("#settings-close").click()
    expect(sidebar).not_to_have_class(re.compile(r"mobile-open"))


def test_mobile_add_recipient_in_drawer(mobile_page: Page):
    mobile_page.locator("#settings-toggle").click()
    mobile_page.fill("#recipient-add", "mobile@example.com")
    mobile_page.click("#recipient-add-btn")

    chip = mobile_page.locator("#recipient-list .recipient-chip", has_text="mobile@example.com")
    expect(chip).to_be_visible()

    mobile_page.locator("#settings-close").click()
    expect(mobile_page.locator("#chat-main")).to_be_visible()


def test_mobile_no_horizontal_overflow(mobile_page: Page):
    mobile_page.locator("#settings-toggle").click()
    mobile_page.select_option("#mode", "full")
    mobile_page.locator("#settings-close").click()

    overflow = mobile_page.evaluate(
        "() => document.documentElement.scrollWidth <= window.innerWidth + 2"
    )
    assert overflow is True


def test_mobile_user_message_stays_in_viewport(mobile_page: Page):
    mobile_page.fill("#prompt", "Quick mobile layout check")
    mobile_page.click("#send")

    mobile_page.wait_for_selector(".message-row.user .bubble", timeout=5000)
    user_bubble = mobile_page.locator(".message-row.user .bubble").first
    box = user_bubble.bounding_box()
    viewport = mobile_page.viewport_size
    assert box and viewport
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= viewport["width"] + 2
