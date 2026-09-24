import csv
import psycopg2

# Update these with your actual database credentials
DB_CONFIG = {
    "host": "tfashion-agents-db.cub6mk4och1j.us-east-1.rds.amazonaws.com",
    "dbname": "postgres",
    "user": "postgres_admin",
    "password": "passw0rd",
    "port": "5432"
}

OUTPUT_CSV = "colors.csv"

query = """
SELECT color_id, color_name, color_family
FROM colors
ORDER BY color_id;
"""

def export_colors_to_csv():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query)

        rows = cur.fetchall()
        headers = [desc[0] for desc in cur.description]

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(rows)

        cur.close()
        print(f"Exported {len(rows)} rows to {OUTPUT_CSV}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    export_colors_to_csv()