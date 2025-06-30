"""
@Author: obstacle 
@Time: 27/08/24
@Description: Test for last_run and is_running fields in TweetSchedule model
"""
import os
import unittest
import tempfile
from datetime import datetime, timedelta

from puti.db.schedule_manager import ScheduleManager
from puti.db.model.task.bot_task import TweetSchedule
from puti.constant.base import TaskType


class TestScheduleFields(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create a temporary directory for PUTI_DATA_PATH
        self.temp_dir = tempfile.mkdtemp()
        
        # Set the environment variables
        os.environ['DB_PATH'] = self.temp_db.name
        os.environ['PUTI_DATA_PATH'] = self.temp_dir
        
        # Create an instance of our manager
        self.manager = ScheduleManager()
        self.manager.create_table()
        
    def tearDown(self):
        # Remove the temporary database
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
            
        # Remove the temporary directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            
    def test_create_schedule(self):
        """Test creating a schedule with last_run and is_running fields."""
        # Create a schedule
        schedule = self.manager.create_schedule(
            name="test_schedule",
            cron_schedule="*/5 * * * *",
            enabled=True,
            task_type=TaskType.POST.val
        )
        
        # Check the fields
        self.assertIsNone(schedule.last_run)
        self.assertFalse(schedule.is_running)
        
    def test_update_fields(self):
        """Test updating last_run and is_running fields."""
        # Create a schedule
        schedule = self.manager.create_schedule(
            name="test_schedule",
            cron_schedule="*/5 * * * *", 
            enabled=True,
            task_type=TaskType.POST.val
        )
        
        # Update the fields
        now = datetime.now()
        self.manager.update(schedule.id, {"last_run": now, "is_running": True})
        
        # Retrieve the updated schedule
        updated = self.manager.get_by_id(schedule.id)
        
        # Check the fields
        self.assertIsNotNone(updated.last_run)
        # Compare timestamps, allowing for a small difference in second precision
        time_diff = abs((updated.last_run - now).total_seconds())
        self.assertLess(time_diff, 1)
        self.assertTrue(updated.is_running)
        
    def test_reset_stuck_tasks(self):
        """Test the reset_stuck_tasks method."""
        # Create schedules with various states
        now = datetime.now()
        old_time = now - timedelta(minutes=60)
        
        # Create a non-stuck task (recently updated)
        schedule1 = self.manager.create_schedule(
            name="recent_task",
            cron_schedule="*/5 * * * *",
            enabled=True
        )
        self.manager.update(schedule1.id, {"is_running": True})
        
        # Create a stuck task (updated long ago)
        schedule2 = self.manager.create_schedule(
            name="stuck_task",
            cron_schedule="*/5 * * * *",
            enabled=True
        )
        self.manager.update(schedule2.id, {
            "is_running": True,
            "updated_at": old_time
        })
        
        # Run the reset_stuck_tasks method
        reset_count = self.manager.reset_stuck_tasks(max_minutes=30)
        
        # Check the results
        self.assertEqual(reset_count, 1)
        
        # Check that only the stuck task was reset
        updated1 = self.manager.get_by_id(schedule1.id)
        updated2 = self.manager.get_by_id(schedule2.id)
        
        self.assertTrue(updated1.is_running)
        self.assertFalse(updated2.is_running)


if __name__ == "__main__":
    unittest.main() 