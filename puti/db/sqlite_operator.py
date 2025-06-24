import sqlite3
import os
import json
import threading
import datetime
from typing import List, Optional, Type, Tuple, Any, Dict
from puti.logs import logger_factory
from puti.constant.base import Pathh

lgr = logger_factory.db


class SQLiteOperator:
    _connections = threading.local()

    def __init__(self):
        db_path = os.getenv("PUTI_DATA_PATH")
        if not db_path:
            raise ValueError("PUTI_DATA_PATH environment variable not set.")

        # Ensure the directory exists
        os.makedirs(db_path, exist_ok=True)

        # 使用常量定义的SQLite文件路径，而不是硬编码的文件名
        # 注意: 如果PUTI_DATA_PATH已经指向了正确的目录，我们只需要取文件名部分
        sqlite_filename = os.path.basename(Pathh.SQLITE_FILE.val)
        self.db_file = os.path.join(db_path, sqlite_filename)
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

    def execute_model_table_creation(self, model_type):
        """Create a table for the given model type if it doesn't exist."""
        # Get table name from the model's class attribute
        table_name = model_type.__table_name__
        
        # Generate schema based on model's fields
        fields_schema = []
        for field_name, field_info in model_type.model_fields.items():
            if field_name == 'id':
                fields_schema.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
                continue
                
            field_type = "TEXT"  # Default to TEXT for most field types
            if field_info.annotation == int:
                field_type = "INTEGER"
            elif field_info.annotation == bool:
                field_type = "BOOLEAN"
            elif field_info.annotation == float:
                field_type = "REAL"
                
            fields_schema.append(f"{field_name} {field_type}")
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(fields_schema)}
        );
        """
        
        try:
            self.execute(create_table_sql)
            # lgr.info(f"Table '{table_name}' created or verified.")
        except Exception as e:
            lgr.error(f"Error creating table '{table_name}': {e}")
            raise
            
    def get_model_by_id(self, model_type, record_id: int):
        """Get a single model instance by its ID."""
        table_name = model_type.__table_name__
        query = f"SELECT * FROM {table_name} WHERE id = ?"
        
        try:
            row = self.fetchone(query, (record_id,))
            if row:
                return self._row_to_model(model_type, row)
            return None
        except Exception as e:
            lgr.error(f"Error fetching record with ID {record_id} from {table_name}: {e}")
            return None
            
    def get_models(self, model_type, where_clause: str = "", params: Tuple = ()):
        """Get a list of model instances based on a WHERE clause."""
        table_name = model_type.__table_name__
        query = f"SELECT * FROM {table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
            
        try:
            rows = self.fetchall(query, params)
            return [self._row_to_model(model_type, row) for row in rows]
        except Exception as e:
            lgr.error(f"Error fetching records from {table_name}: {e}")
            return []
            
    def insert_model(self, model_instance):
        """Insert a model instance into the database."""
        # Get table name from the model's class
        table_name = model_instance.__class__.__table_name__
        
        # Convert model to a dictionary, excluding ID field (for auto-increment)
        model_dict = model_instance.model_dump()
        if 'id' in model_dict and model_dict['id'] is None:
            del model_dict['id']
            
        # Prepare field names and placeholders for SQL
        fields = list(model_dict.keys())
        placeholders = ', '.join(['?' for _ in fields])
        
        # Convert complex types to JSON and handle datetime
        values = []
        for field in fields:
            value = model_dict[field]
            if isinstance(value, (dict, list)):
                values.append(json.dumps(value))
            elif isinstance(value, datetime.datetime):
                values.append(value.isoformat())
            else:
                values.append(value)
        
        # Create SQL statement
        query = f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({placeholders})"
        
        try:
            row_id = self.insert(query, tuple(values))
            return row_id
        except Exception as e:
            lgr.error(f"Error inserting record into {table_name}: {e}")
            raise
            
    def _row_to_model(self, model_type, row):
        """Convert a database row to a model instance."""
        # Convert Row object to dictionary
        row_dict = dict(row)
        
        # Process fields that require special handling
        model_fields = model_type.model_fields
        for field_name, field_value in list(row_dict.items()):
            # Check if field exists in model
            if field_name not in model_fields:
                continue
                
            field_info = model_fields[field_name]
            
            # Handle JSON fields (dicts, lists)
            if field_info.annotation in (dict, list) or hasattr(field_info.annotation, '__origin__') and field_info.annotation.__origin__ in (dict, list):
                if field_value and isinstance(field_value, str):
                    try:
                        row_dict[field_name] = json.loads(field_value)
                    except json.JSONDecodeError:
                        lgr.warning(f"Failed to decode JSON for field {field_name}: {field_value}")
                        
            # Handle datetime fields
            elif field_info.annotation == datetime.datetime:
                if field_value and isinstance(field_value, str):
                    try:
                        row_dict[field_name] = datetime.datetime.fromisoformat(field_value)
                    except ValueError:
                        lgr.warning(f"Failed to parse datetime for field {field_name}: {field_value}")
        
        # Create model instance
        try:
            return model_type(**row_dict)
        except Exception as e:
            lgr.error(f"Error creating {model_type.__name__} instance from row: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
