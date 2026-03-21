################################################################
# Module    :   Check database connection  
# Author    :   Eric S. Viacrusis 
# Date      :   March 16, 2026
#
# UPDATES   
# March 20, 2026 - using .env file for database credentials
################################################################

import os
from dotenv import load_dotenv
import psycopg2

#Load environment variables from .env file
load_dotenv()

print("Starting connection test...")
print("DB_HOST =", os.getenv("DB_HOST"))
print("DB_NAME =", os.getenv("DB_NAME"))
print("DB_USER =", os.getenv("DB_USER"))
print("DB_PORT =", os.getenv("DB_PORT"))
print("DB_PASSWORD =", os.getenv("DB_PASSWORD"))


try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        sslmode="require"
    )
    print("Connected successfully!")
    conn.close()
    print("Connection closed.")
except Exception as e:
    print("Connection failed:")
    print(e)