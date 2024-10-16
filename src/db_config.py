import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import os
import pathlib

BASE_DIR = pathlib.Path(__file__).parent.parent
keys_path = os.path.join(BASE_DIR, 'keys.env')
load_dotenv(dotenv_path=keys_path)

db_host = os.getenv('DB_HOST')
db_pass = os.getenv('DB_PASS')
db_user = os.getenv('DB_USER')

def create_connection():
    try:
        connection = psycopg2.connect(
            database="packto_db",
            user=db_user,
            password=db_pass,
            host="localhost",#db_host,#"host.docker.internal",
            port="5432"
        )
        print("Connection to PostgreSQL DB successful")
        return connection
    except OperationalError as e:
        print(f"The error '{e}' occurred")
        return None
    

def execute_query(connection, query, params=None):
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        if "returning" in query.lower():
            # For INSERT queries, fetch the returned ID
            connection.commit()
            result = cursor.fetchone()
            return result[0] if result else None
        else:
            print("proper execute")
            connection.commit()
            print("Query executed successfully")
            return None
    except Exception as e:
        print(f"The error '{e}' occurred")
        connection.rollback()
    finally:
        cursor.close()


def fetch_query(connection, query, params=None):
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results
    except Exception as e:
        print(f"The error '{e}' occurred")
        return []


connection = create_connection()
if connection:
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS pcaps (
        pcap_id SERIAL PRIMARY KEY,
        pcap_filepath TEXT NOT NULL UNIQUE,
        csv_filepath TEXT,
        ragged_yet BOOLEAN,
        vectorstore_path TEXT,
        subnet TEXT,
        chat_history JSONB,
        init_qa JSONB,
        graph_state JSONB
    );  
    '''
    execute_query(connection, create_table_query)

    connection.close()
    
    
connection = create_connection()
if connection:
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS protocols (
        proto_id SERIAL PRIMARY KEY,
        proto_filepath TEXT
    );  
    '''
    execute_query(connection, create_table_query)

    connection.close()