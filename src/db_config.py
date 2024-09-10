import psycopg2
from psycopg2 import OperationalError

def create_connection():
    try:
        connection = psycopg2.connect(
            database="packto_db",
            user="postgres",
            password="[REDACTED]",
            host="localhost",
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
        if query.strip().lower().startswith("insert") and "returning" in query.lower():
            # For INSERT queries, fetch the returned ID
            result = cursor.fetchone()
            return result[0] if result else None
        else:
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
        chat_history JSONB,
        init_qa JSONB
    );  
    '''
    execute_query(connection, create_table_query)

    connection.close()
    