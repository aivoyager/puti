"""
@Author: obstacle
@Time: 27/06/20 10:00
@Description: A base manager for handling database operations for a specific model.
"""
from typing import Type, List, Optional, Dict, Any, Tuple, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
import json
import datetime

from puti.db.model import Model
from puti.db.sqlite_operator import SQLiteOperator
from puti.logs import logger_factory

lgr = logger_factory.db

# Define a generic type variable
T = TypeVar('T', bound=Model)


class BaseManager(BaseModel, Generic[T]):
    """A generic model manager that inherits from BaseModel."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_type: Type[T] = Field(..., description="The Pydantic model class this manager operates on.")
    db_operator: Optional[SQLiteOperator] = Field(None, description="The database operator instance.")

    _table_name: str = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        """Initialize the database operator and table name after model validation."""
        if not issubclass(self.model_type, Model):
            raise TypeError("The model_type must be a subclass of puti.db.model.Model")

        # If no db_operator is provided, create a default one.
        if self.db_operator is None:
            self.db_operator = SQLiteOperator()

        self._table_name = self.model_type.__table_name__
        self.create_table()

    def get_by_id(self, record_id: int) -> Optional[T]:
        """Retrieves a single model instance by its primary key."""
        return self.db_operator.get_model_by_id(self.model_type, record_id)

    def get_all(self, where_clause: str = "", params: Tuple = ()) -> List[T]:
        """Retrieves all model instances, with an optional filter."""
        return self.db_operator.get_models(self.model_type, where_clause, params)
        
    def get_one(self, where_clause: str = "", params: Tuple = ()) -> Optional[T]:
        """
        Retrieves a single model instance based on a where clause.
        Returns None if no matches are found.
        """
        results = self.get_all(where_clause, params)
        return results[0] if results else None

    def save(self, instance: T) -> int:
        """Saves a model instance (inserts) to the database."""
        if not isinstance(instance, self.model_type):
            raise TypeError(f"Instance must be of type {self.model_type.__name__}")
        
        return self.db_operator.insert_model(instance)

    def update(self, record_id: int, updates: Dict[str, Any]) -> bool:
        """Updates a record in the database."""
        if not updates:
            lgr.warning("No update data provided.")
            return False

        # If this manager handles TweetSchedules and the cron schedule is changing,
        # we need to recalculate the next_run time.
        if self.model_type.__name__ == 'TweetSchedule' and 'cron_schedule' in updates:
            from croniter import croniter
            try:
                now = datetime.datetime.now()
                updates['next_run'] = croniter(updates['cron_schedule'], now).get_next(datetime.datetime)
            except ValueError as e:
                lgr.error(f"Invalid cron expression in update: {updates['cron_schedule']}")
                return False

        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        
        # Serialize dicts/lists to JSON and datetimes to ISO strings
        update_values = []
        for value in updates.values():
            if isinstance(value, (dict, list)):
                update_values.append(json.dumps(value))
            elif isinstance(value, datetime.datetime):
                update_values.append(value.isoformat())
            else:
                update_values.append(value)
        
        params = update_values + [record_id]
        
        query = f"UPDATE {self._table_name} SET {set_clause} WHERE id = ?"
        
        try:
            self.db_operator.execute(query, tuple(params))
            return True
        except Exception as e:
            lgr.error(f"Error updating record ID {record_id} in {self._table_name}: {e}")
            return False
            
    def delete(self, record_id: int, soft_delete: bool = True) -> bool:
        """Deletes a record from the database."""
        if soft_delete:
            return self.update(record_id, {'is_del': True})
        else:
            query = f"DELETE FROM {self._table_name} WHERE id = ?"
            try:
                self.db_operator.execute(query, (record_id,))
                return True
            except Exception as e:
                lgr.error(f"Error deleting record ID {record_id} from {self._table_name}: {e}")
                return False

    def create_table(self):
        """Creates the database table for the model if it doesn't exist."""
        self.db_operator.execute_model_table_creation(self.model_type)
        # lgr.info(f"Table '{self._table_name}' created or verified.")
