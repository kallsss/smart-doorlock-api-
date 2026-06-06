import psycopg
import config.creds as creds

def get_db_connection():

    return psycopg.connect(
        host=creds.db_host,
        port=creds.db_port,
        dbname=creds.db_name,
        user=creds.db_username,
        password=creds.db_password
    )