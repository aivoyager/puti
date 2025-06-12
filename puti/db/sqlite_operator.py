import sqlite3
import os
import threading
from puti.logs import logger_factory

lgr = logger_factory.db


class SqliteOperator:
    _connections = threading.local()

    def __init__(self):
        db_path = os.getenv("PUTI_DATA_PATH")
        if not db_path:
            raise ValueError("PUTI_DATA_PATH environment variable not set.")

        # Ensure the directory exists
        os.makedirs(db_path, exist_ok=True)

        self.db_file = os.path.join(db_path, 'puti.sqlite')
        self._ensure_table_exists()

    def connect(self):
        if not hasattr(self._connections, 'conn') or self._connections.conn is None:
            try:
                self._connections.conn = sqlite3.connect(self.db_file, check_same_thread=False)
                self._connections.conn.row_factory = sqlite3.Row
            except sqlite3.Error as e:
                lgr.error(f"Error connecting to SQLite database: {e}")
                raise
        return self._connections.conn

    def close(self):
        if hasattr(self._connections, 'conn') and self._connections.conn is not None:
            self._connections.conn.close()
            self._connections.conn = None

    def execute(self, sql, params=None):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor
        except sqlite3.Error as e:
            lgr.error(f"Error executing query: {sql} with params: {params}. Error: {e}")
            conn.rollback()
            raise

    def fetchone(self, sql, params=None):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchone()

    def fetchall(self, sql, params=None):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchall()

    def insert(self, sql, params=None):
        cursor = self.execute(sql, params)
        return cursor.lastrowid

    def update(self, sql, params=None):
        cursor = self.execute(sql, params)
        return cursor.rowcount

    def delete(self, sql, params=None):
        cursor = self.execute(sql, params)
        return cursor.rowcount

    def _ensure_table_exists(self):
        """Ensures the 'twitter_mentions' table exists in the database."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS twitter_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            author_id TEXT,
            mention_id TEXT UNIQUE,
            parent_id TEXT,
            data_time TEXT,
            replied BOOLEAN
        );
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            conn.commit()
        except sqlite3.Error as e:
            lgr.error(f"Error ensuring table exists: {e}")
        finally:
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
