##################################################
# Module    :   Check database connection  
# Author    :   Eric S. Viacrusis 
# Date      :   March 16, 2026 
##################################################

import psycopg2

from config import Config


config = Config.from_env()

conn = psycopg2.connect(
    host=config.db_host,
    dbname=config.db_name,
    user=config.db_user,
    password=config.db_password,
    port=config.db_port,
)

conn.autocommit = True 
cursor = conn.cursor()
create_db = """CREATE database orders_db"""
cursor.execute(create_db)
create_table = """
    CREATE TABLE Customer(
        customer_id INT NOT NULL, 
        last_name VARCHAR(30) NOT NULL, 
        first_name VARCHAR(30) NOT NULL, 
        state VARCHAR(2) NOT NULL 
    );
"""

cursor.execute(create_table)
insert_query = "INSERT INTO Customer (customer_id, last_name, first_name, state) values (1, 'Jones', 'Jack', 'CA')"
cursor.execute(insert_query)
select_query = "SELECT * FROM Customer;"
cursor.execute(select_query)
print(cursor.fetchall())

# cleanup databases 
delete_db = "DROP DATABASE orders_db"
cursor.execute(delete_db)

conn.close()

 

