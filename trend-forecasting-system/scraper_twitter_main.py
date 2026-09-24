from __future__ import annotations

print("🚀 SCRIPT STARTED")

import csv
import json
import random
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

from playwright.sync_api import sync_playwright


@dataclass
class Post:
    account: str
    post_url: str
    post_id: str
    text: str
    datetime: str
    reply_count: Optional[str]
    repost_count: Optional[str]
    like_count: Optional[str]
    view_count: Optional[str]


def polite_pause(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def safe_text(locator) -> str:
    try:
        if locator.count() > 0:
            return locator.first.inner_text().strip()
    except Exception:
        pass
    return ""


def safe_attr(locator, attr: str) -> str:
    try:
        if locator.count() > 0:
            value = locator.first.get_attribute(attr)
            return value or ""
    except Exception:
        pass
    return ""


def parse_twitter_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_date_start(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def parse_date_end(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
    )


def in_date_range(dt_str, start_date, end_date):
    post_dt = parse_twitter_datetime(dt_str)
    if post_dt is None:
        return False

    if start_date and post_dt < start_date:
        return False
    if end_date and post_dt > end_date:
        return False

    return True


def extract_posts_from_page(page, account, max_posts, start_date, end_date):
    print("🔍 Extracting posts...")

    posts = []
    seen_ids = set()

    articles = page.locator("article")
    print("📊 Total <article> elements:", articles.count())

    tweet_articles = page.locator("article[data-testid='tweet']")
    print("📊 Tweet articles found:", tweet_articles.count())

    for i in range(min(tweet_articles.count(), 20)):
        article = tweet_articles.nth(i)

        text = safe_text(article.locator("[data-testid='tweetText']"))
        time_link = article.locator("time").locator("..")

        post_url = safe_attr(time_link, "href")
        dt = safe_attr(article.locator("time"), "datetime")

        print("------")
        print("Post URL:", post_url)
        print("Datetime:", dt)
        print("Text preview:", text[:50])

        if post_url.startswith("/"):
            post_url = f"https://x.com{post_url}"

        match = re.search(r"/status/(\d+)", post_url)
        post_id = match.group(1) if match else ""

        if not post_id or post_id in seen_ids:
            continue

        seen_ids.add(post_id)

        if not in_date_range(dt, start_date, end_date):
            continue

        posts.append(
            Post(
                account=account,
                post_url=post_url,
                post_id=post_id,
                text=text,
                datetime=dt,
                reply_count=None,
                repost_count=None,
                like_count=None,
                view_count=None,
            )
        )

        if len(posts) >= max_posts:
            break

    print(f"✅ Extracted {len(posts)} matching posts")
    return posts


def scrape_x_profile(account, max_posts, start_date, end_date):
    url = f"https://x.com/{account}"

    with sync_playwright() as p:
        print("🌐 Launching Chrome with persistent profile...")

        context = p.chromium.launch_persistent_context(
            user_data_dir="./chrome_profile",
            channel="chrome",
            headless=False
        )

        page = context.pages[0] if context.pages else context.new_page()

        print(f"➡️ Opening {url}")
        page.goto(url)
        polite_pause(5, 7)

        print("📄 Current URL:", page.url)
        print("📄 Page title:", page.title())

        print("⏳ Waiting for content...")
        page.wait_for_timeout(5000)

        posts = extract_posts_from_page(
            page, account, max_posts, start_date, end_date
        )

        context.close()
        return posts


def main():
    print("📥 Arguments:", sys.argv)

    if len(sys.argv) < 2:
        print("Usage:")
        print("python scraper_twitter_main.py <account> [max_posts] [start_date] [end_date]")
        return

    account = sys.argv[1]
    max_posts = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    start_date = parse_date_start(sys.argv[3]) if len(sys.argv) > 3 else None
    end_date = parse_date_end(sys.argv[4]) if len(sys.argv) > 4 else None

    posts = scrape_x_profile(
        account, max_posts, start_date, end_date
    )

    print(f"📊 FINAL RESULT: {len(posts)} posts")

    if posts:
        with open(f"{account}_posts.json", "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in posts], f, indent=2, ensure_ascii=False)
        print("💾 File saved!")
    else:
        print("⚠️ No posts matched your criteria")


if __name__ == "__main__":
    main()