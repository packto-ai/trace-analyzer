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
        connection.commit()
        print("Query executed successfully")
        cursor.close()
    except Exception as e:
        print(f"The error '{e}' occurred")
        connection.rollback()


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
