import os
import sqlite3
from functools import lru_cache

from loguru import logger

from common.config import env_settings


def setup_table(db_path: str):

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # SQL to create a table
    sql_query = """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        task_id TEXT NOT NULL,
        status TEXT NOT NULL,
        video_url TEXT NOT NULL
    );
    """

    # Execute the create table command
    cursor.execute(sql_query)

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    logger.info(f"table created at {db_path}")
    return conn


@lru_cache
def get_db_connection():
    db_path = os.path.join(env_settings.DATA_DIR, "martech_model.db")
    if not os.path.exists(db_path):
        os.mkdir(db_path)
        conn = setup_table(db_path)
    else:
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
