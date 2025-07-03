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
from puti.llm.actions.x_bot import GenerateTweetAction, PublishTweetAction, ReplyToRecentUnrepliedTweetsAction, ContextAwareReplyToMentionsAction
from puti.llm.roles.agents import Ethan, EthanG
from puti.llm.workflow import Workflow
from puti.llm.graph import Graph, Vertex
from puti.db.schedule_manager import ScheduleManager
from puti.db.task_state_guard import TaskStateGuard


lgr = logger_factory.default


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
            _ethan_instance = EthanG(disable_history_search=True)
            
        # Health check: ensure the instance is a valid EthanG object.
        try:
            if not isinstance(_ethan_instance, EthanG):
                lgr.warning("Invalid EthanG instance detected, recreating...")
                _ethan_instance = EthanG(disable_history_search=True)
        except Exception as e:
            # Error recovery: if any error occurs during the check, recreate the instance.
            lgr.error(f"Error accessing EthanG instance: {str(e)}. Recreating...")
            _ethan_instance = EthanG(disable_history_search=True)
            
        return _ethan_instance


TASK_MAP = {
    TaskType.POST.val: 'celery_queue.simplified_tasks.generate_tweet_task',
    TaskType.REPLY.val: 'celery_queue.simplified_tasks.reply_to_tweets_task',
    TaskType.CONTEXT_REPLY.val: 'celery_queue.simplified_tasks.context_aware_reply_task',
    TaskType.RETWEET.val: 'celery_queue.simplified_tasks.unimplemented_task',
    TaskType.UNIMPLEMENTED.val: 'celery_queue.simplified_tasks.unimplemented_task'
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
                lgr.info(f'Evaluating task "{schedule.name}" (ID: {schedule.id}) with type={schedule.task_type}')
                
                # To correctly handle overdue tasks, always initialize croniter with the current time.
                cron = croniter(schedule.cron_schedule, now)
                next_run_time = cron.get_prev(datetime)  # Get the most recent past scheduled time
                
                # A task should run if its last execution time is before the most recent scheduled time.
                # This correctly handles tasks that were scheduled to run in the past but haven't executed yet.
                last_run = schedule.last_run or datetime.fromtimestamp(0)
                
                lgr.info(f'Schedule "{schedule.name}" - last_run: {last_run}, next_run_time: {next_run_time}, now: {now}')
                lgr.info(f'Schedule "{schedule.name}" - should run? {last_run < next_run_time}')
                
                if last_run < next_run_time:
                    lgr.info(f'Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')
                    
                    # Get task type and parameters
                    task_type = schedule.task_type
                    params = schedule.params or {}
                    lgr.info(f'Task params for "{schedule.name}": {params}')
                    
                    # Find the corresponding Celery task in the task map
                    task_name = TASK_MAP.get(task_type)
                    if not task_name:
                        lgr.error(f"No task found for type '{task_type}' on schedule {schedule.id}. Skipping.")
                        continue
                    
                    lgr.info(f'Task name for "{schedule.name}": {task_name}')

                    # Mark as running before dispatching the task and include the schedule_id
                    manager.update(schedule.id, {"is_running": True})
                    lgr.info(f'Marked "{schedule.name}" as running in the database')

                    # Dispatch the task to Celery with schedule_id and other params
                    from celery import current_app
                    task_kwargs = {"schedule_id": schedule.id, **params}
                    lgr.info(f'Dispatching task "{task_name}" with kwargs: {task_kwargs}')
                    task = current_app.send_task(task_name, kwargs=task_kwargs)
                    lgr.info(f'Task dispatched with ID: {task.id}')
                    
                    # After triggering, calculate the actual next run time from now.
                    new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                    
                    # Note: last_run will be set by TaskStateGuard upon successful completion.
                    # Here, we only update task_id and next_run.
                    schedule_updates = {
                        "next_run": new_next_run,
                        "task_id": task.id
                    }
                    manager.update(schedule.id, schedule_updates)
                    
                    lgr.info(f'Schedule "{schedule.name}" executed. Next run at {new_next_run}. Task ID: {task.id}')
                else:
                    lgr.info(f'Schedule "{schedule.name}" does not need to run yet')

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
def generate_tweet_task(self, schedule_id, topic, **kwargs):
    """
    Generates and publishes a tweet using a Graph Workflow.
    This is a sync wrapper around an async operation.
    Args:
        topic: The topic for tweet generation.
    """
    import asyncio
    from puti.db.task_state_guard import TaskStateGuard

    async def _async_run():
        task_id = self.request.id
        with TaskStateGuard.for_task(task_id=task_id, schedule_id=schedule_id) as guard:
            lgr.info(f'[Task {task_id}] generate_tweet_task started, topic: {topic}')
            guard.update_state(status="generating_tweet")

            generate_tweet_action = GenerateTweetAction(topic=topic)
            post_tweet_action = PublishTweetAction()
            ethan = get_ethan_instance()

            generate_tweet_vertex = Vertex(id='generate_tweet', action=generate_tweet_action)
            post_tweet_vertex = Vertex(id='post_tweet', action=post_tweet_action, role=ethan)

            graph = Graph()
            graph.add_vertices(generate_tweet_vertex, post_tweet_vertex)
            graph.add_edge(generate_tweet_vertex.id, post_tweet_vertex.id)
            graph.set_start_vertex(generate_tweet_vertex.id)

            guard.update_state(status="running_workflow")
            workflow = Workflow(graph=graph)
            resp = await workflow.run_until_vertex(post_tweet_vertex.id)

            lgr.info(f'[Task {task_id}] Completed successfully')
            return resp

    try:
        return asyncio.run(_async_run())
    except Exception as e:
        lgr.error(f"Error in generate_tweet_task: {e}", exc_info=True)
        raise


@shared_task(bind=True)
def reply_to_tweets_task(self, schedule_id, **kwargs):
    """
    Celery task to reply to recent tweets based on a schedule.
    This is a sync wrapper around an async operation.
    """
    import asyncio
    from puti.db.task_state_guard import TaskStateGuard

    async def _async_run():
        with TaskStateGuard.for_task(task_id=self.request.id, schedule_id=schedule_id) as guard:
            lgr.info(f"Executing reply to tweets task for schedule_id: {schedule_id} with params: {kwargs}")

            time_value = int(kwargs.get('time_value', 7))
            time_unit = str(kwargs.get('time_unit', 'days'))

            graph = Graph()
            reply_action = ReplyToRecentUnrepliedTweetsAction(time_value=time_value, time_unit=time_unit)
            reply_tweet_vertex = Vertex(id='reply_tweet', action=reply_action, role=get_ethan_instance())
            graph.add_vertices(reply_tweet_vertex)
            graph.set_start_vertex(reply_tweet_vertex.id)
            workflow = Workflow(graph=graph)
            guard.update_state(status="reply_tweet")

            resp = await workflow.run()

            lgr.info(f"Reply task for schedule {schedule_id} completed. Final result: {resp}")
            return str(resp)

    try:
        return asyncio.run(_async_run())
    except Exception as e:
        lgr.error(f"Error in reply_to_tweets_task: {e}", exc_info=True)
        raise e


@shared_task(bind=True)
def context_aware_reply_task(self, schedule_id, **kwargs):
    """
    Celery task to find and reply to mentions with full conversation context awareness.
    This task traces back the conversation thread for each mention before replying.
    
    Args:
        schedule_id: The ID of the schedule triggering this task.
        **kwargs: Additional parameters including:
            - time_value: How far back to look for mentions (default: 7)
            - time_unit: Unit of time ('days' or 'hours', default: 'days')
            - max_depth: Maximum depth to trace conversation history (default: 5)
            - max_mentions: Maximum number of mentions to process (default: 5)
    """
    import asyncio
    from puti.db.task_state_guard import TaskStateGuard

    async def _async_run():
        with TaskStateGuard.for_task(task_id=self.request.id, schedule_id=schedule_id) as guard:
            lgr.info(f"Executing context-aware reply task for schedule_id: {schedule_id} with params: {kwargs}")

            # Extract parameters with defaults
            time_value = int(kwargs.get('time_value', 7))
            time_unit = str(kwargs.get('time_unit', 'days'))
            max_depth = int(kwargs.get('max_depth', 5))
            max_mentions = int(kwargs.get('max_mentions', 5))

            # Create the graph with the context-aware reply action
            graph = Graph()
            context_reply_action = ContextAwareReplyToMentionsAction(
                time_value=time_value,
                time_unit=time_unit,
                max_context_depth=max_depth,
                max_mentions=max_mentions
            )
            
            # Use the action in a vertex with Ethan
            context_reply_vertex = Vertex(
                id='context_aware_reply', 
                action=context_reply_action, 
                role=get_ethan_instance()
            )
            
            # Set up the graph
            graph.add_vertices(context_reply_vertex)
            graph.set_start_vertex(context_reply_vertex.id)
            
            # Update task state and run the graph directly
            guard.update_state(status="context_aware_reply")
            resp = await graph.run()

            lgr.info(f"Context-aware reply task for schedule {schedule_id} completed. Final result: {resp}")
            return str(resp)

    try:
        return asyncio.run(_async_run())
    except Exception as e:
        lgr.error(f"Error in context_aware_reply_task: {e}", exc_info=True)
        raise


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
        
        return 'Scheduler state checked'
        
    except Exception as e:
        lgr.error(f"Error in auto_manage_scheduler: {str(e)}")
        return 'Error checking scheduler state' 