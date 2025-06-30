"""
@Author: obstacle
@Time: 25/07/24 15:16
@Description: Simplified Celery tasks for scheduler demos
"""
import os
import asyncio
import json
import traceback
import threading
from datetime import datetime

from celery import shared_task
from croniter import croniter
from puti.logs import logger_factory
from puti.constant.base import TaskType
from puti.llm.actions.x_bot import GenerateTweetAction, PublishTweetAction
from puti.llm.roles.agents import Ethan, EthanG
from puti.llm.workflow import Workflow
from puti.llm.graph import Graph, Vertex
from puti.db.schedule_manager import ScheduleManager
from puti.db.task_state_guard import TaskStateGuard


lgr = logger_factory.default


def run_async(coro):
    """
    Runs and manages an asyncio event loop for a coroutine from a synchronous context.
    This creates a new event loop for each call to ensure isolation,
    preventing "Event loop is closed" errors in long-running applications like Celery.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Instantiate the Ethan role at the module level to ensure it's created only once.
_ethan_instance = None
# Add a thread lock to protect _ethan_instance in a multi-threaded environment.
_ethan_lock = threading.RLock()


# Function to safely get the Ethan instance.
def get_ethan_instance():
    """
    Safely retrieves the EthanG instance in a thread-safe manner.
    
    Implements lazy loading and error recovery:
    1. Creates the instance only on the first access.
    2. Attempts to recreate the instance if it encounters issues.
    
    Returns:
        An EthanG instance.
    """
    global _ethan_instance
    
    with _ethan_lock:
        # Lazy loading: if the instance doesn't exist, create it.
        if _ethan_instance is None:
            lgr.info("Creating new EthanG instance")
            _ethan_instance = EthanG()
            
        # Health check: ensure the instance is a valid EthanG object.
        try:
            if not isinstance(_ethan_instance, EthanG):
                lgr.warning("Invalid EthanG instance detected, recreating...")
                _ethan_instance = EthanG()
        except Exception as e:
            # Error recovery: if any error occurs during the check, recreate the instance.
            lgr.error(f"Error accessing EthanG instance: {str(e)}. Recreating...")
            _ethan_instance = EthanG()
            
        return _ethan_instance


TASK_MAP = {
    TaskType.POST.val: 'celery_queue.simplified_tasks.generate_tweet_task',
    TaskType.REPLY.val: 'celery_queue.simplified_tasks.unimplemented_task',
    TaskType.RETWEET.val: 'celery_queue.simplified_tasks.unimplemented_task',
}


@shared_task()
def check_dynamic_schedules():
    """
    Checks for enabled schedules in the database and triggers them if they are due.
    This is the core scheduler logic.
    """
    now = datetime.now()
    lgr.info(f'Core scheduler check running at {now}')

    try:
        manager = ScheduleManager()
        
        # First, reset any stuck tasks
        reset_count = manager.reset_stuck_tasks(max_minutes=30)
        if reset_count > 0:
            lgr.info(f'Reset {reset_count} stuck tasks')
            
        # Get all enabled tasks
        schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        lgr.info(f'Found {len(schedules)} active schedules to evaluate.')

        for schedule in schedules:
            # Skip running tasks
            if schedule.is_running:
                lgr.debug(f'Schedule "{schedule.name}" is already running, skipping.')
                continue

            try:
                # Determine the base time for calculating the next run
                last_run = schedule.last_run or datetime.fromtimestamp(0)
                
                # Check if the task should run
                cron = croniter(schedule.cron_schedule, last_run)
                next_run_time = cron.get_next(datetime)

                if next_run_time <= now:
                    lgr.info(f'Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')
                    
                    # Get task type and parameters
                    task_type = schedule.task_type
                    params = schedule.params or {}
                    
                    # Find the corresponding Celery task in the task map
                    task_name = TASK_MAP.get(task_type)
                    if not task_name:
                        lgr.error(f"No task found for type '{task_type}' on schedule {schedule.id}. Skipping.")
                        continue

                    # Mark as running before dispatching the task
                    manager.update(schedule.id, {"is_running": True})

                    # Dispatch the task to Celery
                    from celery import current_app
                    task = current_app.send_task(task_name, kwargs=params)
                    
                    # Update the schedule's run time and task ID
                    new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                    
                    # Note: last_run will be set by TaskStateGuard upon successful completion.
                    # Here, we only update task_id and next_run.
                    schedule_updates = {
                        "next_run": new_next_run,
                        "task_id": task.id
                    }
                    manager.update(schedule.id, schedule_updates)
                    
                    lgr.info(f'Schedule "{schedule.name}" executed. Next run at {new_next_run}. Task ID: {task.id}')

            except Exception as e:
                lgr.error(f'Error processing schedule {schedule.id} ("{schedule.name}"): {str(e)}')
                # Reset task state on error
                manager.update(schedule.id, {"is_running": False})

    except Exception as e:
        lgr.error(f'Fatal error in check_dynamic_schedules: {str(e)}. {traceback.format_exc()}')

    return 'ok'


@shared_task(bind=True)
def unimplemented_task(self, **kwargs):
    """A placeholder for task types that are not yet implemented."""
    lgr.warning(f"Task '{self.name}' with type is not implemented yet. Params: {kwargs}")
    return f"Task type not implemented."


@shared_task(bind=True)
def generate_tweet_task(self, topic: str = None):
    """
    Generates and publishes a tweet using a Graph Workflow.

    Args:
        topic: The topic for tweet generation.
    """
    from puti.db.schedule_manager import ScheduleManager
    from puti.db.task_state_guard import TaskStateGuard

    task_id = self.request.id
    
    # Use TaskStateGuard to ensure the task state is always updated correctly.
    with TaskStateGuard.for_task(task_id=task_id) as guard:
        lgr.info(f'[Task {task_id}] generate_tweet_task started, topic: {topic}')
        
        # You can update additional states here if needed.
        guard.update_state(status="generating_tweet")

        # Create action instances.
        generate_tweet_action = GenerateTweetAction(topic=topic)
        post_tweet_action = PublishTweetAction()
        
        # Use the module-level Ethan instance to avoid repeated creation.
        ethan = get_ethan_instance()

        # Create workflow graph nodes.
        generate_tweet_vertex = Vertex(id='generate_tweet', action=generate_tweet_action)
        post_tweet_vertex = Vertex(id='post_tweet', action=post_tweet_action, role=ethan)

        # Build the workflow graph.
        graph = Graph()
        graph.add_vertices(generate_tweet_vertex, post_tweet_vertex)
        graph.add_edge(generate_tweet_vertex.id, post_tweet_vertex.id)
        graph.set_start_vertex(generate_tweet_vertex.id)

        # Update task status.
        guard.update_state(status="running_workflow")

        # Execute the workflow.
        workflow = Workflow(graph=graph)
        resp = run_async(workflow.run_until_vertex(post_tweet_vertex.id))
        
        # No need to manually update task status here; TaskStateGuard handles it automatically.
        # On successful completion, it automatically sets is_running=False, pid=None, and last_run=start_time.
        
        # Log completion information.
        lgr.info(f'[Task {task_id}] Completed successfully')
        return resp


@shared_task()
def auto_manage_scheduler():
    """
    Automatically manages the scheduler's state.
    - If there are active tasks but the scheduler is not running, it starts the scheduler.
    - If there are no active tasks and the scheduler is running, it can optionally be stopped (depending on configuration).
    """
    try:
        from puti.db.schedule_manager import ScheduleManager
        from puti.scheduler import BeatDaemon
        
        manager = ScheduleManager()
        daemon = BeatDaemon()
        
        # Get all enabled and not deleted tasks
        active_schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        # Get all running tasks
        running_schedules = manager.get_all(where_clause="is_running = 1 AND is_del = 0")
        
        # Check if the scheduler needs to be started
        if active_schedules and not daemon.is_running():
            lgr.info(f'Found {len(active_schedules)} active schedules but scheduler is not running. Starting scheduler...')
            daemon.start()
            lgr.info('Scheduler auto-started')
            return 'Scheduler auto-started'
        
        # Check if the scheduler can be stopped (optional logic)
        # For example, if there are no active tasks and no tasks currently running
        if not active_schedules and not running_schedules and daemon.is_running():
            lgr.info('No active or running schedules. Scheduler will continue to run for now.')
            # You could add logic here to stop the scheduler if desired:
            # daemon.stop()
            # lgr.info('Scheduler auto-stopped')
            # return 'Scheduler auto-stopped'
            
        return 'Scheduler status checked, no action needed'
        
    except Exception as e:
        lgr.error(f'Error in auto_manage_scheduler: {str(e)}')
        return f'Error: {str(e)}' 