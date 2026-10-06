from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir="./chrome_profile",
        channel="chrome",
        headless=False
    )

    page = context.new_page()
    page.goto("https://x.com/home")

    input("Log in manually in the browser, then press Enter here to save the browser profile...")

    context.close()

print("Chrome profile saved in ./chrome_profile")