"""
@Author: obstacle
@Time: 25/06/20 10:30
@Description: Utility functions for managing dynamic tweet schedules
"""
import json
import datetime
from croniter import croniter
from typing import Dict, Any, Optional, List, Union

from puti.db.sqlite_operator import SQLiteOperator
from puti.db.model.task.bot_task import TweetSchedule
from puti.logs import logger_factory
from puti.db.base_manager import BaseManager

lgr = logger_factory.default


class ScheduleManager(BaseManager):
    """Manages tweet schedules with specific business logic."""

    def save(self, schedule: TweetSchedule) -> int:
        """
        Saves a new schedule after validating the cron expression and setting the next run time.

        Args:
            schedule: A TweetSchedule model instance.

        Returns:
            The ID of the created schedule.
        """
        # Validate cron expression and set the initial next_run time
        try:
            now = datetime.datetime.now()
            schedule.next_run = croniter(schedule.cron_schedule, now).get_next(datetime.datetime)
        except ValueError as e:
            lgr.error(f"Invalid cron expression: {schedule.cron_schedule}")
            raise ValueError(f"Invalid cron expression: {e}")

        return super().save(schedule)

    def get_by_name(self, name: str) -> Optional[TweetSchedule]:
        """Retrieves a single schedule by its unique name."""
        schedules = self.get_all(where_clause="name = ? AND is_del = 0", params=(name,))
        return schedules[0] if schedules else None

    @staticmethod
    def create_schedule_table():
        """Create the tweet_schedules table if it doesn't exist"""
        db = SQLiteOperator()
        db.execute_model_table_creation(TweetSchedule)
        lgr.info("Tweet schedule table created or verified")
        
    @staticmethod
    def update_schedule(schedule_id: int, updates: Dict[str, Any]) -> bool:
        """
        Updates an existing schedule in the database from a dictionary of updates.

        Args:
            schedule_id: ID of the schedule to update.
            updates: A dictionary containing the fields to update.

        Returns:
            True if successful, False otherwise.
        """
        db = SQLiteOperator()

        # Prevent key fields from being updated this way
        updates.pop('id', None)
        updates.pop('created_at', None)

        if not updates:
            lgr.warning("No fields provided to update.")
            return False

        # If the cron schedule is part of the update, recalculate the next_run time
        if 'cron_schedule' in updates:
            try:
                now = datetime.datetime.now()
                updates['next_run'] = croniter(updates['cron_schedule'], now).get_next(datetime.datetime).isoformat()
            except ValueError as e:
                lgr.error(f"Invalid cron expression in update: {updates['cron_schedule']}")
                return False

        # Always update the updated_at timestamp
        updates['updated_at'] = datetime.datetime.now().isoformat()

        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        params = list(updates.values()) + [schedule_id]

        query = f"UPDATE {TweetSchedule.__table_name__} SET {set_clause} WHERE id = ?"

        try:
            db.execute(query, tuple(params))
            lgr.info(f"Updated schedule ID {schedule_id}.")
            return True
        except Exception as e:
            lgr.error(f"Error updating schedule ID {schedule_id}: {e}")
            return False
    
    @staticmethod
    def delete_schedule(schedule_id: int) -> bool:
        """
        Soft deletes a schedule by marking it as deleted.

        Args:
            schedule_id: ID of the schedule to delete.

        Returns:
            True if successful, False otherwise.
        """
        lgr.info(f"Soft deleting schedule ID {schedule_id}")
        return ScheduleManager.update_schedule(schedule_id, {'is_del': True})
    
    @staticmethod
    def get_all_schedules(include_deleted: bool = False) -> List[TweetSchedule]:
        """
        Gets all schedules from the database as model instances.

        Args:
            include_deleted: Whether to include soft-deleted schedules.

        Returns:
            A list of TweetSchedule model instances.
        """
        db = SQLiteOperator()
        where_clause = "" if include_deleted else "is_del=0"
        return db.get_models(TweetSchedule, where_clause)
    
    @staticmethod
    def get_schedule(schedule_id: int) -> Optional[TweetSchedule]:
        """
        Gets a specific schedule by ID as a model instance.

        Args:
            schedule_id: ID of the schedule to retrieve.

        Returns:
            A TweetSchedule model instance or None if not found.
        """
        db = SQLiteOperator()
        return db.get_model_by_id(TweetSchedule, schedule_id) 