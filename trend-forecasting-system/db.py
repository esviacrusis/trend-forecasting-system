###############################################################################
# Module    :   Global Function to Connect to PostgreSQL Database 
# Author    :   Eric S. Viacrusis 
# Date      :   March 27, 2026
#
# UPDATES   
# March 27, 2026 - create a global function to connect to PostgreSQL database and return connection object
# April 10, 2026 - Query brands from database and print results
###############################################################################

import psycopg2
import pandas as pd

from config import Config


class DataProvider:
    def __init__(self):
        self.conn_params = Config.from_env().db_connection_params()

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    # def get_brands(self):
    #     query = """
    #         SELECT brand_name, description
    #         FROM brands
    #         ORDER BY brand_name;
    #     """

    #     with self.get_connection() as conn:
    #         df = pd.read_sql_query(query, conn)

    #     return query,

    def get_brands(self):
        query = """
            SELECT brand_name, description
            FROM brands
            ORDER BY brand_name;
        """

        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        return query, df
