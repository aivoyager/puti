"""
@Author: obstacle
@Time: 25/06/20 11:15
@Description: Test for dynamic tweet scheduling system
"""
import pytest
import datetime
from puti.db.schedule_manager import ScheduleManager
from puti.db.model.task.bot_task import TweetSchedule
from puti.db.sqlite_operator import SQLiteOperator


@pytest.fixture
def test_db_path(tmp_path):
    """Provides a temporary database path for integration tests."""
    return str(tmp_path / "test_dynamic_schedule.sqlite")


@pytest.fixture
def schedule_manager(test_db_path):
    """
    Provides a ScheduleManager instance connected to a temporary, clean database for each test.
    """
    # Use a temporary database for the test
    db_operator = SQLiteOperator(db_file=test_db_path)
    
    # Instantiate the manager, injecting the test db_operator.
    # The manager's post_init method will handle table creation.
    manager = ScheduleManager(model_type=TweetSchedule, db_operator=db_operator)
    
    # Clean up the table before each test run for hygiene
    manager.db_operator.execute("DELETE FROM tweet_schedules")
    
    yield manager
    
    # Optional: cleanup after test if needed, though tmp_path handles file deletion
    manager.db_operator.close()


def test_create_schedule(schedule_manager):
    """Test creating a new tweet schedule using the manager."""
    new_schedule = TweetSchedule(
        name="test_hourly_tweet",
        cron_schedule="0 * * * *",
        enabled=True,
        task_parameters={"topic": "Technology trends"}
    )
    schedule_id = schedule_manager.save(new_schedule)
    
    assert schedule_id is not None
    
    retrieved_schedule = schedule_manager.get_by_id(schedule_id)
    assert retrieved_schedule is not None
    assert retrieved_schedule.name == "test_hourly_tweet"
    assert retrieved_schedule.task_parameters["topic"] == "Technology trends"
    assert retrieved_schedule.next_run is not None


def test_update_schedule(schedule_manager):
    """Test updating an existing tweet schedule."""
    schedule_to_update = TweetSchedule(
        name="test_daily_tweet",
        cron_schedule="0 12 * * *",
        enabled=True
    )
    schedule_id = schedule_manager.save(schedule_to_update)
    
    updates = {
        "name": "test_daily_tweet_updated",
        "cron_schedule": "0 15 * * *",
        "task_parameters": {"topic": "AI updates"}
    }
    success = schedule_manager.update(schedule_id, updates)
    
    assert success
    
    retrieved_schedule = schedule_manager.get_by_id(schedule_id)
    assert retrieved_schedule.name == "test_daily_tweet_updated"
    assert retrieved_schedule.cron_schedule == "0 15 * * *"
    assert retrieved_schedule.task_parameters["topic"] == "AI updates"


def test_disable_and_enable_schedule(schedule_manager):
    """Test disabling and re-enabling a schedule."""
    schedule_to_toggle = TweetSchedule(
        name="test_weekly_tweet",
        cron_schedule="0 9 * * 1",
        enabled=True
    )
    schedule_id = schedule_manager.save(schedule_to_toggle)
    
    schedule_manager.update(schedule_id, {"enabled": False})
    retrieved_schedule = schedule_manager.get_by_id(schedule_id)
    assert not retrieved_schedule.enabled
    
    schedule_manager.update(schedule_id, {"enabled": True})
    retrieved_schedule_after_enable = schedule_manager.get_by_id(schedule_id)
    assert retrieved_schedule_after_enable.enabled


def test_delete_schedule(schedule_manager):
    """Test soft-deleting a schedule."""
    schedule_to_delete = TweetSchedule(
        name="test_to_delete",
        cron_schedule="0 0 * * *",
        enabled=True
    )
    schedule_id = schedule_manager.save(schedule_to_delete)
    
    success = schedule_manager.delete(schedule_id)
    assert success
    
    # Should not be found in a normal query
    all_schedules = schedule_manager.get_all(where_clause="is_del = 0")
    assert schedule_id not in [s.id for s in all_schedules]
    
    # Should still exist in the database but be marked as deleted
    deleted_schedule = schedule_manager.get_by_id(schedule_id)
    assert deleted_schedule.is_del


def test_list_schedules(schedule_manager):
    """Test listing all schedules."""
    for i in range(3):
        schedule = TweetSchedule(
            name=f"test_list_{i}",
            cron_schedule=f"{i} {i} * * *",
            enabled=(i % 2 == 0)
        )
        schedule_manager.save(schedule)
    
    all_schedules = schedule_manager.get_all(where_clause="name LIKE 'test_list_%'")
    assert len(all_schedules) == 3
