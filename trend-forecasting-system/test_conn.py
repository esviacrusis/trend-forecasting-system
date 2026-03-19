import psycopg2

#ENDPOINT = "tfashion-agents-db.cub6mk4och1j.us-east-1.rds.amazonaws.com"
#DBNAME = "tfashion-agents-db"
#USER = "postgres_admin"
#PWD = "passww0rd"

print("Starting connection test...")

try:
    conn = psycopg2.connect(
        host="tfashion-agents-db.cub6mk4och1j.us-east-1.rds.amazonaws.com",
        database="postgres",
        user="postgres_admin",
        password="passw0rd",
        port=5432
    )
    print("Connected successfully!")
    conn.close()
    print("Connection closed.")
except Exception as e:
    print("Connection failed:")
    print(e)