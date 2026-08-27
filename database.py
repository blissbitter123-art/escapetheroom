import sqlite3
import os
import logging
from config import DATABASE_PATH, SCHEMA_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('database')

def get_db():
    """Get a database connection with sqlite3.Row factory."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables safely using executescript."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")
    
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = get_db()
    try:
        conn.executescript(schema_sql)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing database schema: {e}")
        raise e
    finally:
        conn.close()

def query_db(query, args=(), one=False):
    """Execute query and fetch results."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

def execute_db(query, args=()):
    """Execute DML statement and commit."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def insert_db(query, args=()):
    """Execute insert statement and return lastrowid."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
