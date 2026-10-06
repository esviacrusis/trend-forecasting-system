###############################################################################
# Module    :   This is the main page
# Author    :   Eric S. Viacrusis 
# Date      :   March 27, 2026
#
# UPDATES   
# March 27, 2026 - create streamlit app to display data from database
# April 3, 2026 - create run tracker to generate unique run ID for each execution of the script
###############################################################################


import psycopg2

from ingestion_vogue import ingest
from cv_pipeline import run_cv


from run_tracker import start_run, end_run
from config import Config

# from cv import run_cv
# from nlp import run_nlp
# from features import run_features
# from train import run_training
# from predict import run_prediction
# from insights import run_insights
# from moodboards import run_moodboards




def main():
    run_id = start_run("full_pipeline")
    config = Config.from_env()


    try:

        # conn = psycopg2.connect(
        #     host="localhost",
        #     dbname="your_db",
        #     user="your_user",
        #     password="your_password"
        # )

        # cursor = conn.cursor()


        # 🔹 Start run
        #config = {"source": "vogue"}
        #run_id = start_run(cursor, "vogue_ingest", config, "Initial ingestion")



        # 🔹 Your ingestion logic
        #ingest(cursor, run_id)


        # originally was:



        #------------------ Ingestion -----------------------------------
        #ingest(run_id, config)


        #------------------ Computer Vision Processing ------------------

        # Data input Sample
        # Spring Selling 2023 - Fashion Show Sep to Oct 2022
        # Brand : Chanel


         #run_cv(run_id)
        #run_cv(run_id, config)
        run_cv(run_id, config)

        # run_nlp(run_id)
        # run_features(run_id)
        # run_training(run_id)
        # run_prediction(run_id)
        # run_insights(run_id)
        # run_moodboards(run_id)

        # 🔹 End run
        #end_run(cursor, run_id)

        #conn.commit()






    finally:
        end_run(run_id)


if __name__ == "__main__":
    main()
