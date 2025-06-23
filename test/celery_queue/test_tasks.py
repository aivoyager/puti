"""
@Author: obstacle
@Time: 25/06/20 17:00
@Description: Tests for Celery tasks
"""
import pytest
import datetime
from unittest.mock import patch, AsyncMock

from celery_queue.tasks import generate_tweet_task, check_dynamic_schedules
from puti.db.schedule_manager import ScheduleManager
from puti.db.model.task.bot_task import TweetSchedule
from puti.db.sqlite_operator import SQLiteOperator


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Fixture to set up and tear down the database for each test."""
    manager = ScheduleManager()
    manager.create_table()
    db = manager._db
    db.execute("DELETE FROM tweet_schedules WHERE name LIKE 'test_celery_%'")
    yield
    db.execute("DELETE FROM tweet_schedules WHERE name LIKE 'test_celery_%'")


@pytest.mark.asyncio
@patch('celery_queue.tasks.Workflow', autospec=True)
async def test_celery_generate_tweet_task(mock_workflow_class):
    """
    Tests the `generate_tweet_task` to ensure it correctly initializes and runs the tweet generation workflow.
    """
    mock_workflow_instance = mock_workflow_class.return_value
    mock_workflow_instance.run_until_vertex = AsyncMock(return_value="Tweet successfully posted!")

    result = await generate_tweet_task()

    mock_workflow_class.assert_called_once()
    mock_workflow_instance.run_until_vertex.assert_awaited_once_with('post_tweet')
    assert result == "Tweet successfully posted!"


@patch('celery_queue.tasks.generate_tweet_task', new_callable=AsyncMock)
def test_celery_check_dynamic_schedules(mock_generate_tweet_task):
    """
    Tests the `check_dynamic_schedules` task to verify it finds and executes scheduled tasks.
    """
    mock_generate_tweet_task.return_value = "Mocked tweet success!"

    schedule_manager = ScheduleManager()
    new_schedule = TweetSchedule(
        name="test_celery_dynamic_schedule",
        cron_schedule="* * * * *",
        enabled=True
    )
    schedule_id = schedule_manager.save(new_schedule)

    result = check_dynamic_schedules()

    assert result == 'ok'
    mock_generate_tweet_task.assert_called_once()

    updated_schedule = schedule_manager.get_by_id(schedule_id)
    assert updated_schedule is not None
    assert updated_schedule.last_run is not None
    assert updated_schedule.next_run is not None

    last_run_time = updated_schedule.last_run
    assert (datetime.datetime.now() - last_run_time).total_seconds() < 5 