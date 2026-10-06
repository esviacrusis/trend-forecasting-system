##################################################################################
# Module    :   Generate a unique run ID for each execution of the script
# Author    :   Eric S. Viacrusis
# Date      :   March 30, 2026
#
# UPDATES
# March 20: using .env file for database credentials
# March 27: create sql query to test connection and display data from database
#################################################################################

# run_tracker.py

import uuid
from datetime import datetime


def start_run(pipeline_name: str):
    run_id = str(uuid.uuid4())
    started_at = datetime.utcnow()

    print(f"🚀 Started run: {run_id}")
    print(f"Pipeline: {pipeline_name}")
    print(f"Start time: {started_at}")

    return run_id


def end_run(run_id: str):
    finished_at = datetime.utcnow()

    print(f"✅ Finished run: {run_id}")
    print(f"End time: {finished_at}")

#explain this: import uuid
# import json
# from datetime import datetime


# def start_run(cursor, pipeline_name: str, params: dict | None = None, notes: str | None = None) -> str:
#     """
#     Creates a new run entry in the runs table and returns run_id.
#     """

#     run_id = str(uuid.uuid4())

#     cursor.execute("""
#         INSERT INTO runs (run_id, pipeline_name, params_json, notes)
#         VALUES (%s, %s, %s::jsonb, %s)
#     """, (
#         run_id,
#         pipeline_name,
#         json.dumps(params or {}),
#         notes
#     ))

#     return run_id


# def end_run(cursor, run_id: str):
#     """
#     Marks the run as finished.
#     """

#     cursor.execute("""
#         UPDATE runs
#         SET finished_at = NOW()
#         WHERE run_id = %s
#     """, (run_id,))