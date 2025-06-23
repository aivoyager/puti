import sqlite3
import os
import json
import threading
import datetime
from typing import Any, List, Dict, Optional, Type, Tuple, Union
from pydantic import BaseModel, Field, PrivateAttr
from pathlib import Path

from puti.logs import logger_factory
from puti.db.model import Model
from puti.conf.config import conf

lgr = logger_factory.db


def get_default_db_path():
    """Reads the database path from the global config, with a fallback."""
    try:
        # Access the path from the centrally loaded configuration
        path = conf.cc.module['db']['sqlite']['path']
        return path
    except (KeyError, AttributeError):
        # Fallback for environments where config might not be fully loaded
        return str(Path.home() / 'puti' / 'db.sqlite')


class SQLiteOperator(BaseModel):
    """Enhanced SQLite operator that inherits from BaseModel for configuration."""
    db_file: str = Field(default_factory=get_default_db_path,
                         description="Path to the SQLite database file.")

    # PrivateAttr is used for attributes that are not part of the Pydantic model
    # but are needed for the instance's state.
    _connections: threading.local = PrivateAttr(default_factory=threading.local)

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook to set up the database file and directory."""
        # Ensure the directory for the database file exists
        db_path = os.path.dirname(self.db_file)
        os.makedirs(db_path, exist_ok=True)
        
        lgr.debug(f"SQLiteOperator initialized with database: {self.db_file}")

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
        """Execute an SQL query and return the cursor or result depending on the query type"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            conn.commit()
            
            if sql.strip().upper().startswith("INSERT"):
                return cursor.lastrowid
            elif sql.strip().upper().startswith(("UPDATE", "DELETE")):
                return cursor.rowcount
            else:
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

    def _ensure_tables_exist(self):
        """Ensures the necessary tables exist in the database."""
        # This check is now better handled by the manager for each model.
        # This method can be removed or left for global tables. For now, we pass.
        pass
    
    def execute_model_table_creation(self, model_class: Type[Model]):
        """Create a table based on a pydantic model definition"""
        fields = []
        for name, field in model_class.model_fields.items():
            sqlite_type = self._convert_field_type(field.annotation)
            field_def = f"{name} {sqlite_type}"
            
            if name == "id":
                field_def += " PRIMARY KEY AUTOINCREMENT"
            
            if field.is_required():
                # Pydantic's required fields don't have a default, so they are NOT NULL by default
                # unless they are Optional.
                if "Optional" not in str(field.annotation):
                    field_def += " NOT NULL"
            
            if field.default is not None and field.default is not ...:
                if isinstance(field.default, str):
                    field_def += f" DEFAULT '{field.default}'"
                elif isinstance(field.default, bool):
                    field_def += f" DEFAULT {1 if field.default else 0}"
                elif isinstance(field.default, (dict, list)):
                    # Correctly serialize dict/list defaults to a JSON string
                    field_def += f" DEFAULT '{json.dumps(field.default)}'"
                else:
                    field_def += f" DEFAULT {field.default}"
            
            if field.json_schema_extra and field.json_schema_extra.get('unique', False):
                field_def += " UNIQUE"
            
            if field.json_schema_extra and field.json_schema_extra.get('dft_time', '') == 'now':
                field_def += " DEFAULT CURRENT_TIMESTAMP"
                
            fields.append(field_def)
            
        fields_sql = ", ".join(fields)
        query = f"CREATE TABLE IF NOT EXISTS {model_class.__table_name__} ({fields_sql});"
        
        try:
            self.execute(query)
            lgr.info(f"Created or verified table: {model_class.__table_name__}")
            return True
        except Exception as e:
            lgr.error(f"Error creating table {model_class.__table_name__}: {e}")
            return False
    
    def insert_model(self, model_instance: Model) -> int:
        """Insert a model instance into its corresponding table"""
        table_name = model_instance.__class__.__table_name__
        
        excluded = ['id']
        data = model_instance.model_dump()
        columns = [field for field in data.keys() if field not in excluded]
        values = []
        
        for col in columns:
            val = data[col]
            if isinstance(val, datetime.datetime):
                val = val.isoformat()
            elif isinstance(val, (dict, list)):
                val = json.dumps(val)
            elif isinstance(val, bool):
                val = 1 if val else 0
            
            values.append(val)
        
        placeholders = ", ".join(["?" for _ in columns])
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        try:
            return self.execute(query, tuple(values))
        except Exception as e:
            lgr.error(f"Error inserting model into {table_name}: {e}")
            raise
            
    def update_model(self, model_instance: Model, where_clause: str, where_params: Tuple = ()) -> int:
        """Update a record based on a model instance"""
        table_name = model_instance.__class__.__table_name__
        excluded = ['id', 'created_at']
        data = model_instance.model_dump()
        update_cols = [f"{field}=?" for field in data.keys() if field not in excluded]
        update_vals = [data[field] for field in data.keys() if field not in excluded]
        
        query = f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE {where_clause}"
        params = tuple(update_vals) + where_params
        
        try:
            return self.execute(query, params)
        except Exception as e:
            lgr.error(f"Error updating {table_name}: {e}")
            raise
    
    def _process_row_for_model(self, model_class: Type[Model], row: sqlite3.Row) -> Dict:
        """Converts a database row into a dictionary suitable for Pydantic model instantiation."""
        if not row:
            return {}
        
        row_dict = {key: row[key] for key in row.keys()}
        
        for name, field in model_class.model_fields.items():
            if name in row_dict and row_dict[name] is not None:
                field_type = field.annotation
                # Handle Optional[T] by getting T
                if getattr(field_type, '__origin__', None) in (Union, Optional):
                    type_args = [arg for arg in field_type.__args__ if arg is not type(None)]
                    if type_args:
                        field_type = type_args[0]

                # Deserialize JSON strings to dicts/lists
                if getattr(field_type, '__origin__', None) in (dict, list) and isinstance(row_dict[name], str):
                    try:
                        row_dict[name] = json.loads(row_dict[name])
                    except json.JSONDecodeError:
                        lgr.warning(f"Could not decode JSON for field {name}: {row_dict[name]}")
                
                # Parse datetime strings to datetime objects
                elif field_type is datetime.datetime and isinstance(row_dict[name], str):
                    try:
                        row_dict[name] = datetime.datetime.fromisoformat(row_dict[name])
                    except ValueError:
                        # Try another common format if fromisoformat fails
                        try:
                            row_dict[name] = datetime.datetime.strptime(row_dict[name], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                             lgr.warning(f"Could not parse datetime for field {name}: {row_dict[name]}")

        return row_dict

    def get_model_by_id(self, model_class: Type[Model], record_id: int) -> Optional[Model]:
        """Retrieve a model instance by ID"""
        table_name = model_class.__table_name__
        query = f"SELECT * FROM {table_name} WHERE id = ?"
        
        try:
            row = self.fetchone(query, (record_id,))
            if row:
                processed_dict = self._process_row_for_model(model_class, row)
                return model_class(**processed_dict)
            return None
        except Exception as e:
            lgr.error(f"Error retrieving {model_class.__name__} with ID {record_id}: {e}")
            raise
    
    def get_models(self, model_class: Type[Model], where_clause: str = "", params: Tuple = ()) -> List[Model]:
        """Retrieve multiple model instances based on a where clause"""
        table_name = model_class.__table_name__
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
            
        try:
            rows = self.fetchall(query, params)
            return [model_class(**self._process_row_for_model(model_class, row)) for row in rows]
        except Exception as e:
            lgr.error(f"Error retrieving {model_class.__name__} instances: {e}")
            return []
    
    @staticmethod
    def _convert_field_type(python_type: Any) -> str:
        type_mapping = {
            int: "INTEGER", str: "TEXT", float: "REAL", bool: "BOOLEAN",
            datetime.datetime: "TIMESTAMP", dict: "TEXT", list: "TEXT",
        }
        
        origin = getattr(python_type, '__origin__', None)
        if origin in (Union, Optional):
            # For Optional[T], get the type T
            type_args = [arg for arg in python_type.__args__ if arg is not type(None)]
            if not type_args:
                return "TEXT" # Should not happen for a well-formed Optional
            type_arg = type_args[0]
            return type_mapping.get(type_arg, "TEXT")
        
        return type_mapping.get(python_type, "TEXT")
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
