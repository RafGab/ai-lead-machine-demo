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

    connection.commit()
    connection.close()