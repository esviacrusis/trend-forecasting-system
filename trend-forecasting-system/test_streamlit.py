###############################################################################
# Module    :   Create Steamlit app to display data from database  
# Author    :   Eric S. Viacrusis 
# Date      :   March 27, 2026
#
# UPDATES   
# March 27, 2026 - create streamlit app to display data from database
###############################################################################

from db import get_connection
import streamlit as st

conn = None

try: 

    st.title("My First Streamlit App")
    st.write("Hello, World!")

    name = st.text_input("Enter your name:")
    if name:
        st.write(f"Hello, {name}!")

    st.title("Don't Push me!")
    if st.button("Don't Push me!"):
        st.write("WTF?! You pushed the button!")

    st.title("Connect to PostgreSQL Database and Display Table Names")
    if st.button("Connect to Database"):

        # Create a SQL query to test the connection and display data from the database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        table_names = cursor.fetchall()
        conn.close()

        st.write("Table Names:")
        for name in table_names:
            st.write(f"- {name[0]}")

except Exception as e:
    st.write("Connection failed:")
    st.write(e)

finally:
    if conn is not None:
        conn.close()
        print("Connection closed.")