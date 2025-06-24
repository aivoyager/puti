"""
@Author: obstacle
@Time: 25/07/24 15:16
@Description: Simplified Celery tasks for scheduler demos
"""
import asyncio
import json
import traceback
from datetime import datetime

from celery import shared_task
from croniter import croniter
from puti.logs import logger_factory

lgr = logger_factory.default


@shared_task()
def check_dynamic_schedules():
    """
    Checks for dynamic schedules in the database and triggers tasks as needed.
    This task is the heartbeat of the dynamic scheduler system and should be
    scheduled to run frequently (e.g., every minute).
    """
    now = datetime.now()
    lgr.info(f'Checking dynamic schedules at {now}')

    try:
        # Use the schedule manager for better database interaction
        from puti.db.schedule_manager import ScheduleManager
        manager = ScheduleManager()
        
        schedules = manager.get_active_schedules()
        lgr.info(f'Found {len(schedules)} active schedules')

        for schedule in schedules:
            # Skip schedules that are already running
            if schedule.is_running:
                lgr.debug(f'Schedule "{schedule.name}" is already running, skipping.')
                continue
                
            # A robust way to check if a task should have run.
            # We iterate from the last known run time up to the current time.
            # This ensures we don't miss runs if the service was down.
            last_run = schedule.last_run or datetime.fromtimestamp(0)
            cron = croniter(schedule.cron_schedule, last_run)
            
            # Get the next scheduled run time based on the last execution
            next_run_time = cron.get_next(datetime)

            if next_run_time <= now:
                lgr.info(f'[Scheduler] Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')

                # Extract parameters from the schedule
                params = schedule.params or {}
                topic = params.get('topic')

                # Mark the task as running in the database
                manager.update_schedule(schedule.id, is_running=True)
                
                # Asynchronously trigger the target task via Celery worker
                task = generate_tweet_task.delay(topic=topic)
                
                # Update the schedule's timestamps and task info in the database
                new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                schedule_updates = {
                    "last_run": now,
                    "next_run": new_next_run,
                    "task_id": task.id
                }
                manager.update_schedule(schedule.id, **schedule_updates)
                
                lgr.info(f'[Scheduler] Schedule "{schedule.name}" executed. Next run at {new_next_run}.')

    except Exception as e:
        lgr.error(f'[Scheduler] Error checking dynamic schedules: {str(e)}. {traceback.format_exc()}')

    return 'ok'


@shared_task(bind=True)
def generate_tweet_task(self, topic: str = None):
    """
    Simplified task that simulates generating and posting a tweet.
    Accepts an optional topic to guide tweet generation.
    """
    start_time = datetime.now()
    task_id = self.request.id
    
    try:
        # Find the schedule associated with this task
        from puti.db.schedule_manager import ScheduleManager
        manager = ScheduleManager()
        
        # Try to update running status 
        try:
            import os
            pid = os.getpid()
            
            # Try to find the schedule by task_id if we have one
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update_schedule(schedule.id, pid=pid)
                lgr.info(f'[Task {task_id}] Updated schedule {schedule.name} with PID {pid}')
        except Exception as e:
            lgr.warning(f'Could not update PID for task {task_id}: {str(e)}')
        
        lgr.info(f'[Task {task_id}] generate_tweet_task started, topic: {topic}')
        
        # Simulate tweet generation
        tweet_text = f"This is a simulated tweet about {topic if topic else 'something interesting'}! #simulation #demo"
        lgr.info(f'[Task {task_id}] Generated tweet: {tweet_text}')
        
        # Simulate a delay
        import time
        time.sleep(2)
        
        lgr.info(f'[Task {task_id}] Simulated posting tweet to platform')
        
        # Task completed successfully
        try:
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update_schedule(schedule.id, is_running=False, pid=None)
                lgr.info(f'[Task {task_id}] Completed schedule {schedule.name} successfully')
        except Exception as e:
            lgr.warning(f'Could not update status for task {task_id}: {str(e)}')
        
        lgr.info(f'[Task {task_id}] Completed in {(datetime.now() - start_time).total_seconds():.2f} seconds')
        return {"status": "success", "tweet": tweet_text}
    except Exception as e:
        # Task failed
        try:
            from puti.db.schedule_manager import ScheduleManager
            manager = ScheduleManager()
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update_schedule(schedule.id, is_running=False, pid=None)
                lgr.error(f'[Task {task_id}] Failed schedule {schedule.name}: {str(e)}')
        except Exception as inner_e:
            lgr.warning(f'Could not update status for task {task_id}: {str(inner_e)}')
            
        lgr.error(f'[Task {task_id}] Failed: {str(e)}. {traceback.format_exc()}')
    finally:
        lgr.info(f'[Task {task_id}] Execution finished')
    return {"status": "error", "message": str(e) if 'e' in locals() else "Unknown error"} 