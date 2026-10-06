################################################################################################
# Module    :   Ingestion for Vogue Images
# Author    :   Eric S. Viacrusis
# Date      :   April 1, 2026
#
# UPDATES
# April 1   :   This module saves the image files to AWS S3 bucket instead of local storage. It uses the S3Client class from aws_s3.py to handle the upload process.
# April 4   :   Add how to insert into postgres
################################################################################################

from aws_s3 import S3Client
from dotenv import load_dotenv
import os
import uuid
import psycopg2
import pandas as pd
import json

#class IngestionVogue:
def __init__(run_id, config):
    ing_run_id = run_id
    ing_config = config

def ingest(run_id, config):
    ingest_run_id = run_id
    ingest_config = config

    print(f"Running ingestion with run_id={ingest_run_id}")

    aws_key = ingest_config.aws_key
    aws_secret = ingest_config.aws_secret
    region = ingest_config.aws_region
    bucket = ingest_config.aws_bucket

    'Generate UUID for this run'
    id = ingest_run_id
    print(id)

    'Step 1: Download image from Vogue Runway to a temporary local path'
    'Place the function for sceen scraping Do a screen scrape and save to temporary location'

    upload_path = "/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/VogueImages/00001-chanel-spring-2026-ready-to-wear-credit-gorunway.webp"

    'Step 2: (a) Upload the image from the temporary local path to AWS S3 bucket using the S3Client class'
    '       (b) Insert a row into PostgreSQL database with the S3 URL of the uploaded image and any relevant metadata (e.g., designer, season, etc.)'
    s3 = S3Client(bucket)

    s3.upload_file(upload_path, "uploads/00001-chanel-spring-2026-ready-to-wear-credit-gorunway.webp")
    s3.download_file("uploads/00001-chanel-spring-2026-ready-to-wear-credit-gorunway.webp", "/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/VogueImages/Downloaded00001-chanel-spring-2026-ready-to-wear-credit-gorunway.webp")

    conn = psycopg2.connect(
        host = ingest_config.db_host,
        database = ingest_config.db_name,
        user = ingest_config.db_user,
        password = ingest_config.db_password,
        port = ingest_config.db_port,
        sslmode = "require"
    )
    print("Connected successfully!")

###########################################################
# Save the S3 URL and metadata to PostgreSQL database
###########################################################

    # Sample metadata - in real implementation, these would be extracted from the image or associated data
    brand = "Chanel"
    season = "Spring"
    year = 2026
    look_number = 1
    image_url = "https://vogue.com/look1.jpg"
    s3_uri = f"s3://{bucket}/uploads/00001-chanel-spring-2026-ready-to-wear-credit-gorunway.webp"
    run_id = ingest_run_id

    cursor = conn.cursor()


    #### Save to table : runs

    pipeline_name = "vogue_ingest"
    params = {"brand": brand, "season": season, "year": year}
    notes = "Ingested image from Vogue runway show"

    cursor.execute("""
    INSERT INTO runs (run_id, pipeline_name, params_json, notes)
    VALUES (%s, %s, %s::jsonb, %s)
    """, (
        run_id,
        pipeline_name,
        json.dumps(params or {}),
        notes
    ))

    #### Save to table : show

    cursor.execute("""
    INSERT INTO shows (brand, season, year)
    VALUES (%s, %s, %s)
    RETURNING show_id
    """, (brand, season, year))

    show_id = cursor.fetchone()[0]

    #### Save to table : look

    cursor.execute("""
    INSERT INTO looks (show_id, look_number, image_url_orig, s3_uri, run_id)
    VALUES (%s, %s, %s, %s, %s)
    """, (show_id, look_number, image_url, s3_uri, run_id))

    #cursor.execute(insert_sql, data)

    conn.commit()
    cursor.close()
    conn.close()

    print("Connection closed.")




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
    start = datetime(2025, 1, 1)
    end = datetime(2025, 3, 31)
    delta = end - start
    return (start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))).isoformat()

with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
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
        "ingested_run_id",
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
        ingested_run_id = str(uuid.uuid4())
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
            ingested_run_id,
            status
        ])

print(f"Created: {out_path}")