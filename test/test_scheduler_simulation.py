"""
@Author: obstacle 
@Time: 27/08/24
@Description: Simulate the scheduler check process
"""
import os
import tempfile
from datetime import datetime, timedelta
import time

from puti.db.schedule_manager import ScheduleManager
from puti.constant.base import TaskType


def test_simulate_scheduler():
    """Simulate the scheduler check process."""
    
    print("=== Scheduler Simulation ===")
    
    # Create a temporary database and data path
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Set environment variables
            os.environ['DB_PATH'] = temp_db.name
            os.environ['PUTI_DATA_PATH'] = temp_dir
            
            # Create manager and table
            manager = ScheduleManager()
            manager.create_table()
            
            # Create a task scheduled for "every minute"
            print("\n1. Creating a task scheduled for 'every minute'...")
            schedule = manager.create_schedule(
                name="test_task",
                cron_schedule="* * * * *",  # Every minute
                enabled=True,
                task_type=TaskType.POST.val,
                params={"topic": "AI"}
            )
            
            print(f"   Task created: ID={schedule.id}, Name={schedule.name}")
            print(f"   Is running: {schedule.is_running}")
            print(f"   Last run: {schedule.last_run}")
            print(f"   Next run: {schedule.next_run}")
            
            # Simulate task execution
            print("\n2. Simulating task execution...")
            now = datetime.now()
            manager.update(schedule.id, {
                "is_running": True,
                "last_run": now,
                "next_run": now + timedelta(minutes=1),
                "task_id": "fake-task-id-123"
            })
            
            # Check the updated schedule
            updated = manager.get_by_id(schedule.id)
            print(f"   Is running: {updated.is_running}")
            print(f"   Last run: {updated.last_run}")
            print(f"   Task ID: {updated.task_id}")
            
            # Simulate task completion
            print("\n3. Simulating task completion...")
            time.sleep(1)  # Short pause
            manager.update(schedule.id, {
                "is_running": False,
                "pid": None
            })
            
            # Check final state
            final = manager.get_by_id(schedule.id)
            print(f"   Is running: {final.is_running}")
            print(f"   Last run: {final.last_run}")
            
            # Simulate task getting stuck
            print("\n4. Simulating a stuck task...")
            manager.update(schedule.id, {
                "is_running": True,
                "updated_at": datetime.now() - timedelta(hours=1)  # Set to 1 hour ago
            })
            
            # Reset stuck tasks
            print("\n5. Resetting stuck tasks...")
            reset_count = manager.reset_stuck_tasks(max_minutes=30)
            
            # Check results
            reset = manager.get_by_id(schedule.id)
            print(f"   Tasks reset: {reset_count}")
            print(f"   Is running after reset: {reset.is_running}")
            
            print("\n=== Simulation Complete ===")
            
        finally:
            # Clean up
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
