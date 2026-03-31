###############################################################################
# Module    :   This is the main page
# Author    :   Eric S. Viacrusis 
# Date      :   March 27, 2026
#
# UPDATES   
# March 27, 2026 - create streamlit app to display data from database
###############################################################################

from db import get_connection
import streamlit as st

try:

    conn = None 

    # Header 
    st.title("The Fashion Agents")
    st.write("Trend Forecasting System for the Fashion Industry")


    if st.button("Start Ingestion"):
        st.write("Run the script to get data from Vogue Runway, Instagram, Twitter and store it in the database.")

    if st.button("Run CV Processing"):
        st.write("Run the computer vision processing script.")

    if st.button("Build Features"):
        st.write("Build features for the machine learning model.")

    if st.button("Train Model"):
        st.write("Train the machine learning model.")

    if st.button("Generate Predictions"):
        st.write("Generate predictions based on the trained model.")

    if st.button("Create Mood Boards"):
        st.write("Create mood boards for the fashion trends.")

except Exception as e:
    st.write("Connection failed:")
    st.write(e)

finally:
    if conn is not None:
        conn.close()
        print("Connection closed.")