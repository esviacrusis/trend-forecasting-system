import csv
import uuid
import random
from datetime import datetime, timedelta

out_path = "/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Dataset/social_posts_clean_utf8.csv"

platform_ids = [1, 2]
post_types = ["original", "repost", "quote", "reply"]
colors = ["cobalt blue", "butter yellow", "cherry red", "sage green", "jet black"]
hashtags_pool = ["fashion", "style", "ootd", "trend", "runway", "cobaltblue", "butteryellow", "cherryred"]
mentions_pool = ["voguerunway", "gucci", "chanel", "prada", "zendaya"]

def random_date():
    start = datetime(2025, 10, 1)
    end = datetime(2025, 3, 31)
    delta = end - start
    return (start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))).isoformat()

with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "post_id",
        "platform_id",
        "created_at",
        "post_type",
        "language",
        "is_reply",
        "text_content",
        "hashtags",
        "mentioned_accounts",
        "media_urls",
        "raw_json_s3_uri",
        "status"
    ])

    for _ in range(500):
        post_id = str(uuid.uuid4())
        platform_id = random.choice(platform_ids)
        created_at = random_date()
        post_type = random.choice(post_types)
        language = "en"
        is_reply = random.choice(["true", "false"])
        color = random.choice(colors)
        text_content = f"Loving this {color} look this season"
        hashtags = "{" + ",".join(random.sample(hashtags_pool, 2)) + "}"
        mentioned_accounts = "{" + random.choice(mentions_pool) + "}"
        media_urls = "{https://images.example.com/" + str(uuid.uuid4()) + ".jpg}"
        raw_json_s3_uri = f"s3://bucket/raw/social/{post_id}.json"
        status = "ingested"

        writer.writerow([
            post_id,
            platform_id,
            created_at,
            post_type,
            language,
            is_reply,
            text_content,
            hashtags,
            mentioned_accounts,
            media_urls,
            raw_json_s3_uri,
            status
        ])

print(f"Created: {out_path}")
