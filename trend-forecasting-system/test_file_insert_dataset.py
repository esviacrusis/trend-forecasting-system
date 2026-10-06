import csv
import uuid
import psycopg2
from psycopg2.extras import execute_batch

from config import Config


config = Config.from_env()


def load_csv_to_social_posts(csv_path: str):
    conn = None
    cursor = None

    try:

        config = Config.from_env()
        conn = psycopg2.connect(
            host=config.db_host,
            dbname=config.db_name,
            user=config.db_user,
            password=config.db_password,
            port=5432
        )
        cursor = conn.cursor()

        run_id = str(uuid.uuid4())

        # Get twitter platform_id
        cursor.execute("SELECT platform_id FROM platforms WHERE name = 'twitter';")
        result = cursor.fetchone()
        if not result:
            raise ValueError("No platform_id found for 'twitter'. Insert it into platforms first.")
        platform_id = result[0]

        # Read CSV once and collect rows + usernames
        csv_rows = []
        usernames = set()

        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                username = (row.get("username") or "").strip()
                created_at = row.get("created_at")
                text_content = row.get("text_content")

                if not username or not created_at:
                    continue

                csv_rows.append({
                    "username": username,
                    "created_at": created_at,
                    "text_content": text_content
                })
                usernames.add(username)

        # Ensure each username exists in accounts
        account_map = {}

        for username in usernames:
            # Try to find existing account
            cursor.execute("""
                SELECT account_id
                FROM accounts
                WHERE platform_id = %s AND handle = %s;
            """, (platform_id, username))
            existing = cursor.fetchone()

            if existing:
                account_map[username] = existing[0]
            else:
                new_account_id = str(uuid.uuid4())

                # Minimal insert for a new account
                cursor.execute("""
                    INSERT INTO accounts (account_id, platform_id, handle)
                    VALUES (%s, %s, %s);
                """, (new_account_id, platform_id, username))

                account_map[username] = new_account_id

        # Build social_posts rows
        post_rows = []
        for row in csv_rows:
            post_rows.append((
                str(uuid.uuid4()),                    # post_id
                platform_id,
                account_map[row["username"]],         # account_id
                row["created_at"],
                row["text_content"],
                run_id
            ))

        # Insert posts
        insert_sql = """
        INSERT INTO social_posts (
            post_id,
            platform_id,
            account_id,
            created_at,
            text_content,
            ingested_run_id
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """

        execute_batch(cursor, insert_sql, post_rows, page_size=500)

        conn.commit()

        print(f"Loaded {len(post_rows)} rows into social_posts")
        print(f"Created/used {len(account_map)} accounts")
        print(f"run_id: {run_id}")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Load failed: {e}")
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    load_csv_to_social_posts("/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Dataset/Twitter Data Set - Sept 9 to OCT 31 2022.csv")