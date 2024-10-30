import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import os
import pathlib


#load the db_url from docker-compose environment variables in the web container
DATABASE_URL = os.getenv("DATABASE_URL")

def create_connection():
    try:
        connection = psycopg2.connect(
            DATABASE_URL
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