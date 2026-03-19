#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  7 11:59:25 2026

@author: eric
"""

#pip install requests python-dotenv

import os 
os.getcwd()

from dotenv import load_dotenv
import os

load_dotenv()

BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")

print(BEARER_TOKEN)


##########

import os
import json
import time
import requests
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()  # reads .env in your working directory

BEARER = os.getenv("X_BEARER_TOKEN")
if not BEARER:
    raise RuntimeError("Missing X_BEARER_TOKEN. Put it in a .env file or your environment variables.")

HEADERS = {"Authorization": f"Bearer {BEARER}"}

BASE_URL = "https://api.x.com/2"  # Some apps use https://api.twitter.com/2; use the base your X app requires.

def username_to_user_id(username: str) -> str:
    """
    Spec Step 1: Username Lookup -> user_id
    """
    url = f"{BASE_URL}/users/by/username/{username}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["data"]["id"]

def fetch_user_timeline(user_id: str, since_id: str | None = None, max_pages: int = 25):
    """
    Spec Step 2: User Timeline + pagination + since_id incremental pull
    """
    url = f"{BASE_URL}/users/{user_id}/tweets"

    params = {
        "max_results": 100,  # adjust based on your tier limits
        "tweet.fields": "id,author_id,created_at,text,lang,public_metrics,entities",
        # Optional expansions if permitted by your tier:
        # "expansions": "attachments.media_keys",
        # "media.fields": "url,preview_image_url,type",
        "exclude": "retweets,replies",  # optional; remove if you want them
    }
    if since_id:
        params["since_id"] = since_id

    all_pages = []
    next_token = None

    for _ in range(max_pages):
        if next_token:
            params["pagination_token"] = next_token

        r = requests.get(url, headers=HEADERS, params=params, timeout=30)

        # Basic backoff if rate-limited (your spec calls for rate-limit respect + backoff) :contentReference[oaicite:9]{index=9}
        if r.status_code == 429:
            time.sleep(60)
            continue

        r.raise_for_status()
        payload = r.json()
        all_pages.append(payload)

        meta = payload.get("meta", {})
        next_token = meta.get("next_token")
        if not next_token:
            break

        time.sleep(1)  # gentle pacing

    return all_pages

def save_raw_pages_locally(username: str, pages: list, out_dir: str = "raw_x"):
    """
    Your architecture stores raw responses immutably (S3 in prod). Locally we mimic that with files. :contentReference[oaicite:10]{index=10}
    """
    os.makedirs(out_dir, exist_ok=True)
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for i, page in enumerate(pages, start=1):
        path = os.path.join(out_dir, f"username={username}_run_date={run_date}_page_{i:04d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(page, f, ensure_ascii=False, indent=2)

def load_checkpoint(username: str, checkpoint_dir: str = "checkpoints"):
    os.makedirs(checkpoint_dir, exist_ok=True)
    path = os.path.join(checkpoint_dir, f"username={username}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_checkpoint(username: str, since_id: str, checkpoint_dir: str = "checkpoints"):
    os.makedirs(checkpoint_dir, exist_ok=True)
    path = os.path.join(checkpoint_dir, f"username={username}.json")
    payload = {"username": username, "since_id": since_id, "updated_at": datetime.now(timezone.utc).isoformat()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def get_max_tweet_id(pages: list) -> str | None:
    """
    After a run, advance checkpoint to the newest tweet ID only if everything succeeded. :contentReference[oaicite:11]{index=11}
    """
    max_id = None
    for page in pages:
        for t in page.get("data", []) or []:
            tid = t.get("id")
            if tid and (max_id is None or int(tid) > int(max_id)):
                max_id = tid
    return max_id

if __name__ == "__main__":
    # Example: pull a curated influencer/brand handle from your annex list (don’t hardcode credentials) :contentReference[oaicite:12]{index=12}
    username = "TheFashionAgents"  # no '@'

    ckpt = load_checkpoint(username)
    since_id = ckpt["since_id"] if ckpt else None

    user_id = username_to_user_id(username)
    pages = fetch_user_timeline(user_id, since_id=since_id)

    # Save raw pages (local stand-in for S3 raw zone) :contentReference[oaicite:13]{index=13}
    save_raw_pages_locally(username, pages)

    # Advance checkpoint only after raw save succeeds (and later after DB load succeeds in prod) :contentReference[oaicite:14]{index=14}
    new_since_id = get_max_tweet_id(pages)
    if new_since_id:
        save_checkpoint(username, new_since_id)

    print(f"Fetched {sum(len(p.get('data', []) or []) for p in pages)} posts for @{username}.")
    
    
    ####################
    
import os
import requests

# environment / config
BEARER = os.environ.get("BEARER_TOKEN") or os.environ.get("API_BEARER_TOKEN") or "<INSERT_BEARER_HERE>"
BASE_URL = "https://api.x.com/2"
username = "TheFashionAgents"

def debug_username_lookup(username, bearer):
    url = f"{BASE_URL}/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {bearer}"}
    print("-> URL:", url)
    print("-> Using bearer token: (first 8 chars) ", (bearer[:8] + "..." if bearer else None))
    try:
        r = requests.get(url, headers=headers, timeout=30)
        print("HTTP status:", r.status_code)
        try:
            print("Response JSON:", r.json())
        except Exception:
            print("Response text:", r.text)
        r.raise_for_status()
        print("User id:", r.json()["data"]["id"])
    except requests.exceptions.HTTPError as e:
        print("HTTPError:", e)
        # show headers too (may include helpful rate-limit or error keys)
        print("Response headers:", r.headers)
    except Exception as e:
        print("Other error:", e)

# Run it
debug_username_lookup(username, BEARER)
    
    
    
