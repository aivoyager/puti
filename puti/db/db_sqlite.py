"""
@Author: obstacle
@Time: 16/01/25 16:21
@Description:  
"""
import sqlite3
import datetime

from queue import Queue, Empty
from typing import Any, List, Optional, Type
from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from puti.constant.base import PuTi

# __all__ = ['SQLiteModelHandlerWithPool', 'dbm_maker']


class SQLiteConnectionPool:
    """SQLite connection pool class."""

    def __init__(self, db_path: str, pool_size: int = 5):
        """
        Initialize SQLiteConnectionPool.

        :param db_path: Path to the SQLite database file.
        :param pool_size: Maximum number of connections in the pool.
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path, check_same_thread=False)  # Allow connections across threads
            conn.row_factory = sqlite3.Row
            self.pool.put(conn)

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection from the pool.

        :return: SQLite connection object.
        """
        try:
            return self.pool.get(timeout=5)
        except Empty:
            raise Exception("No available connections in the pool.")

    def release_connection(self, conn: sqlite3.Connection):
        """
        Release a database connection back to the pool.

        :param conn: SQLite connection object to release.
        """
        self.pool.put(conn)

    def close_all(self):
        """Close all connections in the pool."""
        while not self.pool.empty():
            conn = self.pool.get()
            conn.close()


class SQLiteManagerWithPool:
    """SQLite manager class using connection pool."""

    def __init__(self, pool: SQLiteConnectionPool):
        """
        Initialize SQLiteManagerWithPool.

        :param pool: An instance of SQLiteConnectionPool.
        """
        self.pool = pool

    def execute(self, query: str, params: tuple = ()):
        """
        Execute an SQL query using a pooled connection.

        :param query: SQL query string.
        :param params: Parameters for parameterized queries.
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise e
        finally:
            self.pool.release_connection(conn)

    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Execute a query and return all results using a pooled connection.

        :param query: SQL query string.
        :param params: Parameters for parameterized queries.
        :return: List of query results.
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            self.pool.release_connection(conn)

    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Execute a query and return a single result using a pooled connection.

        :param query: SQL query string.
        :param params: Parameters for parameterized queries.
        :return: Single query result.
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            self.pool.release_connection(conn)


class   SQLiteModelHandlerWithPool:
    """SQLite table model handler using connection pool."""

    def __init__(self, db_manager: SQLiteManagerWithPool, model: Type[BaseModel]):
        """
        Initialize SQLiteModelHandlerWithPool.

        :param db_manager: Instance of SQLiteManagerWithPool.
        :param model: Pydantic model class for the table schema.
        :param table_name: Name of the database table.
        """
        self.db_manager = db_manager
        self.model = model
        self.table_name = model.__table_name__

    def create_table(self):
        """
        Dynamically create a table based on the Pydantic model.
        """
        fields = []
        for name, field in self.model.model_fields.items():
            sqlite_type = self._convert_field_type(field.annotation)
            field_def = f"{name} {sqlite_type}"
            if name == "id":
                field_def += " PRIMARY KEY AUTOINCREMENT"
            elif isinstance(field.default, type(PydanticUndefined)) and field.default_factory is None:
                field_def += " NOT NULL"

            if field.default is not None and not isinstance(field.default, type(PydanticUndefined)):
                if isinstance(field.default, str):
                    field_def += f" DEFAULT '{field.default}'"
                else:
                    field_def += f" DEFAULT {field.default}"
            if name == 'mention_id':
                print()
            if field.json_schema_extra and 'unique' in field.json_schema_extra and field.json_schema_extra.get('unique',
                                                                                                               False) is True:
                field_def += " UNIQUE"
            if field.json_schema_extra and 'dft_time' in field.json_schema_extra and field.json_schema_extra.get(
                    'dft_time', '') == 'now':
                field_def += " DEFAULT CURRENT_TIMESTAMP"
            fields.append(field_def)
        fields_sql = ", ".join(fields)
        query = f"CREATE TABLE IF NOT EXISTS {self.table_name} ({fields_sql});"
        self.db_manager.execute(query)
        return query

    def insert(self, data: BaseModel) -> int:
        """
        Insert a new record.

        :param data: Instance of BaseModel containing the data to insert.
        :return: ID of the newly inserted record.
        """
        excluded = ['created_at', 'id']
        columns = [field for field in data.model_fields.keys() if field not in excluded]
        values = []
        for col in columns:
            val = getattr(data, col)
            if isinstance(val, datetime.datetime):
                val = val.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(val, type(None)) or val == 'None':
                val = ''
            values.append(val)
        placeholders = ", ".join(["?" for _ in columns])
        query = f"""INSERT OR IGNORE INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders});"""
        self.db_manager.execute(query, tuple(values))
        conn = self.db_manager.pool.get_connection()
        last_row_id = conn.cursor().lastrowid
        self.db_manager.pool.release_connection(conn)
        return last_row_id

    def fetch_all(self) -> List[BaseModel]:
        """
        Retrieve all records.

        :return: List of all records as instances of the Pydantic model.
        """
        query = f"SELECT * FROM {self.table_name};"
        rows = self.db_manager.fetchall(query)
        return [self.model(**dict(row)) for row in rows]

    def fetch_by_id(self, record_id: int) -> Optional[BaseModel]:
        """
        Retrieve a single record by ID.

        :param record_id: ID of the record to retrieve.
        :return: The record as an instance of the Pydantic model.
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = ?;"
        row = self.db_manager.fetchone(query, (record_id,))
        return self.model(**dict(row)) if row else None

    def delete_by_id(self, record_id: int):
        """
        Delete a record by ID.

        :param record_id: ID of the record to delete.
        """
        query = f"DELETE FROM {self.table_name} WHERE id = ?;"
        self.db_manager.execute(query, (record_id,))

    @staticmethod
    def _convert_field_type(python_type: Any) -> str:
        """
        Convert Python data types to SQLite data types.

        :param python_type: Python data type.
        :return: Corresponding SQLite data type.
        """
        type_mapping = {
            int: "INTEGER",
            str: "TEXT",
            float: "REAL",
            bool: "BOOLEAN",
            datetime.datetime: "TIMESTAMP",
            Optional[int]: 'INTEGER',
            Optional[float]: 'REAL',
            Optional[str]: 'TEXT',
        }
        return type_mapping.get(python_type, "TEXT")


def dbm_maker(db_path: str = None, pool_size: int = None) -> SQLiteManagerWithPool:
    if not db_path:
        db_path = str((PuTi.ROOT_DIR.val / 'puti' / 'db' / 'alpha.db'))
    if not pool_size:
        pool_size = PuTi.POOL_SIZE.val
    pool = SQLiteConnectionPool(
        db_path=db_path,
        pool_size=pool_size
    )
    db_manager = SQLiteManagerWithPool(pool)
    return db_manager
