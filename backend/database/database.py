import sqlite3

DATABASE_NAME = "ai_lead_machine.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            operation TEXT NOT NULL,
            property_type TEXT NOT NULL,
            city TEXT NOT NULL,
            price REAL NOT NULL,
            bedrooms INTEGER,
            available BOOLEAN DEFAULT 1
        )
    """)

    connection.commit()
    connection.close()