import os
import sqlite3

DATABASE_NAME = os.getenv("DATABASE_PATH", "ai_lead_machine.db")


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_column(connection, table: str, column: str, column_type: str) -> None:
    """
    Añade una columna si la tabla ya existía de una versión anterior
    sin ella (migración segura, no borra datos).
    """

    existing_columns = [
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    ]

    if column not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
        )


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
            bathrooms INTEGER,
            available BOOLEAN DEFAULT 1
        )
    """)

    _ensure_column(connection, "properties", "bathrooms", "INTEGER")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS property_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            FOREIGN KEY (property_id) REFERENCES properties(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_data TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            property_id INTEGER NOT NULL,
            scheduled_at TEXT NOT NULL,
            lead_name TEXT,
            lead_phone TEXT,
            lead_email TEXT,
            calendar_event_id TEXT,
            calendar_status TEXT NOT NULL DEFAULT 'not_configured',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (property_id) REFERENCES properties(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS study_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            nationality TEXT,
            admission TEXT,
            city TEXT,
            start_date TEXT,
            message TEXT,
            contacted BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating INTEGER,
            text TEXT NOT NULL,
            published BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()