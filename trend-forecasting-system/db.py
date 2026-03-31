###############################################################################
# Module    :   Global Function to Connect to PostgreSQL Database 
# Author    :   Eric S. Viacrusis 
# Date      :   March 27, 2026
#
# UPDATES   
# March 27, 2026 - create a global function to connect to PostgreSQL database and return connection object
###############################################################################

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432)
    )