import psycopg2

connection = psycopg2.connect(
    database="packto_db",
    user="postgres",
    password="[REDACTED]",
    host="localhost",
    port="5432"
)

cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    PCAP_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    PCAP_FILEPATH TEXT NOT NULL,
    CSV_FILEPATH TEXT,
    RAGGED_YET BOOLEAN,
    VECTORSTORE_PATH TEXT,
    CHAT_HISTORY JSONB,
    INIT_QA JSONB
)  
''')