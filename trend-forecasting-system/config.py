################################################################################################
# Module    :   Configuration settings for the trend forecasting system   
# Author    :   Eric S. Viacrusis 
# Date      :   April 3, 2026
#
# UPDATES   
# April 3   :   This module contains configuration settings for the trend forecasting system.
################################################################################################

import os
from dataclasses import dataclass
from dotenv import load_dotenv

from typing import Optional


# Load environment variables
load_dotenv()


class ConfigError(Exception):
    """Raised when required environment variables are missing."""
    pass


def get_env_var(key: str, required: bool = True, default: str = None) -> str:
    value = os.getenv(key, default)
    if required and value is None:
        raise ConfigError(f"Missing required environment variable: {key}")
    return value


@dataclass
class Config:
    # Database
    aws_key: str
    aws_secret: str
    aws_region: str
    aws_bucket: str
    db_host: str
    db_name: str
    db_user: str
    db_password: str
    db_port: int

    # Optional
    #s3_bucket: str | None = None
    s3_bucket: Optional[str] = None
    @classmethod
    def from_env(cls):
        return cls(
            #AWS S3
            aws_key = get_env_var("AWS_ACCESS_KEY_ID"),
            aws_secret = get_env_var("AWS_SECRET_ACCESS_KEY"),
            aws_region = get_env_var("AWS_DEFAULT_REGION"),
            aws_bucket = get_env_var("AWS_BUCKET_NAME"),
            
            #PostgreSQL
            db_host=get_env_var("DB_HOST"),
            db_name=get_env_var("DB_NAME"),
            db_user=get_env_var("DB_USER"),
            db_password=get_env_var("DB_PASSWORD"),
            db_port=int(get_env_var("DB_PORT", default="5432")),
            s3_bucket=os.getenv("S3_BUCKET")
        )

            # aws_key = os.getenv("AWS_ACCESS_KEY_ID")
            # aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
            # region = os.getenv("AWS_DEFAULT_REGION")
            # bucket = os.getenv("AWS_BUCKET_NAME")



    def db_connection_params(self) -> dict:
        return {
            "host": self.db_host,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
            "port": self.db_port,
            "sslmode": "require",
        }








# class Config:
#     def __init__(self):
#         self.db_url = os.getenv("DB_URL")
#         self.s3_bucket = os.getenv("S3_BUCKET")

#         conn = None

#         try:
#             print("Starting connection test...")
#             print("DB_HOST =", os.getenv("DB_HOST"))
#             print("DB_NAME =", os.getenv("DB_NAME"))
#             print("DB_USER =", os.getenv("DB_USER"))
#             print("DB_PORT =", os.getenv("DB_PORT"))
#             print("DB_PASSWORD =", os.getenv("DB_PASSWORD"))

#             conn = psycopg2.connect(
#                 host=os.getenv("DB_HOST"),
#                 database=os.getenv("DB_NAME"),
#                 user=os.getenv("DB_USER"),
#                 password=os.getenv("DB_PASSWORD"),
#                 port=os.getenv("DB_PORT"),
#                 sslmode="require"
#             )
#             print("Connected successfully!")
            
#             # Create a SQL query (table names) to test the connection and display data from the database
#             query = """
#             SELECT table_name
#             FROM information_schema.tables
#             WHERE table_schema = 'public'
#             """
#             df = pd.read_sql(query, conn)
            
#             #conn.close()
#             print("Connection closed.")

#             # Print the retrieved table names to verify the connection and data retrieval
#             print(df)


#         except Exception as e:
#             print("Connection failed:")
#             print(e)

#         finally:
#             if conn is not None:
#                 conn.close()
#                 print("Connection closed.") 