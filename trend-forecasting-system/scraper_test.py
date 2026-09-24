from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome",  # uses installed Chrome
        headless=False
    )
    page = browser.new_page()
    page.goto("https://www.thefashionagents.com")
    page.pause()

#input("Press Enter to close browser...")  # 👈 keeps it open
