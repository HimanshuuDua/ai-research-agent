"""Capture production mobile screenshots for visual QA."""
from playwright.sync_api import sync_playwright

BASE = "https://ai-research-agent-ecru-zeta.vercel.app"
OUT = "scripts"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#status .label')?.textContent === 'API ready'",
            timeout=20000,
        )
        page.screenshot(path=f"{OUT}/mobile_home.png")
        print("saved mobile_home.png")

        # Open settings drawer
        page.locator("#settings-toggle").click()
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/mobile_settings.png")
        print("saved mobile_settings.png")
        page.locator("#settings-close").click()

        # Select full mode and show composer email
        page.select_option("#mode", "full")
        page.fill("#composer-email", "me@example.com")
        page.click("#composer-email-add")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{OUT}/mobile_composer.png")
        print("saved mobile_composer.png")

        browser.close()


if __name__ == "__main__":
    main()
