"""
@Author: obstacle
@Time: 28/06/20 10:00
@Description: Unit tests for the CLI scheduler commands using mocks.
"""
import pytest
import os
import puti.bootstrap
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from puti.cli import main
from puti.db.model.task.bot_task import TweetSchedule
from puti.conf.config import conf


@pytest.fixture
def runner():
    """Provides a CliRunner instance for invoking CLI commands."""
    return CliRunner()


# --- Mocked Unit Tests ---

@patch('puti.db.schedule_manager.ScheduleManager')
def test_cli_set_creates_schedule(mock_manager_class, runner):
    """Unit test for `scheduler set`: verifies it calls the manager to create a schedule."""
    # Arrange
    mock_manager_instance = MagicMock()
    mock_manager_instance.get_by_name.return_value = None  # Simulate no schedule exists
    mock_manager_class.return_value = mock_manager_instance

    # Act
    result = runner.invoke(main, [
        'scheduler', 'set',
        '--schedule', '* * * * *',
        '--topic', 'Mocked Topic'
    ])

    # Assert
    assert result.exit_code == 0
    mock_manager_instance.get_by_name.assert_called_once_with('cli_managed_schedule')
    mock_manager_instance.save.assert_called_once()
    saved_schedule = mock_manager_instance.save.call_args[0][0]
    assert saved_schedule.cron_schedule == '* * * * *'
    assert saved_schedule.task_parameters['topic'] == 'Mocked Topic'


@patch('puti.db.schedule_manager.ScheduleManager')
def test_cli_set_updates_schedule(mock_manager_class, runner):
    """Unit test for `scheduler set`: verifies it calls the manager to update a schedule."""
    # Arrange
    existing_schedule = TweetSchedule(id=1, name='cli_managed_schedule', cron_schedule='old')
    mock_manager_instance = MagicMock()
    mock_manager_instance.get_by_name.return_value = existing_schedule
    mock_manager_class.return_value = mock_manager_instance

    # Act
    result = runner.invoke(main, [
        'scheduler', 'set',
        '--schedule', '*/5 * * * *',
        '--topic', 'Updated Topic'
    ])

    # Assert
    assert result.exit_code == 0
    mock_manager_instance.get_by_name.assert_called_once_with('cli_managed_schedule')
    mock_manager_instance.update.assert_called_once_with(1, {
        "cron_schedule": '*/5 * * * *',
        "enabled": True,
        "task_parameters": {"topic": 'Updated Topic'}
    })


@patch('puti.scheduler.SchedulerDaemon')
def test_cli_start_and_stop(mock_daemon_class, runner):
    """Unit test for `scheduler start` and `stop`: verifies they call the daemon."""
    # Test start
    mock_daemon_instance = MagicMock()
    mock_daemon_class.return_value = mock_daemon_instance
    result_start = runner.invoke(main, ['scheduler', 'start'])
    assert result_start.exit_code == 0
    mock_daemon_instance.start.assert_called_once()

    # Test stop
    result_stop = runner.invoke(main, ['scheduler', 'stop'])
    assert result_stop.exit_code == 0
    mock_daemon_instance.stop.assert_called_once()


# --- Non-Mocked / Integration Tests ---

@pytest.fixture
def test_db_path(tmp_path):
    """Provides a temporary database path for integration tests."""
    db_path = str(tmp_path / "test_cli.sqlite")
    # Patch the config *before* the schedule_manager fixture runs
    with patch.dict(conf.cc.module, {"db": {"sqlite": {"path": db_path}}}):
        yield db_path


@pytest.fixture
def schedule_manager(test_db_path):
    """Provides a ScheduleManager instance connected to a temporary database."""
    from puti.db.schedule_manager import ScheduleManager
    from puti.db.sqlite_operator import SQLiteOperator
    from puti.db.model.task.bot_task import TweetSchedule

    # The db_path is already patched in the config
    manager = ScheduleManager(model_type=TweetSchedule)
    manager.db_operator.execute("DELETE FROM tweet_schedules")
    return manager


def test_cli_set_creates_and_updates_schedule_real(runner, schedule_manager, test_db_path):
    """
    Integration test for `scheduler set`: verifies it creates and then updates a schedule.
    """
    # Act 1: Create the schedule
    result_create = runner.invoke(main, [
        'scheduler', 'set',
        '--schedule', '* * * * *',
        '--topic', 'Real Topic'
    ])

    # Assert 1: Creation
    assert result_create.exit_code == 0
    assert "Created new schedule" in result_create.output
    schedule = schedule_manager.get_by_name('cli_managed_schedule')
    assert schedule is not None
    assert schedule.cron_schedule == '* * * * *'
    assert schedule.task_parameters['topic'] == 'Real Topic'
    assert schedule.enabled is True

    # Act 2: Update the schedule
    result_update = runner.invoke(main, [
        'scheduler', 'set',
        '--schedule', '*/10 * * * *',
        '--topic', 'New Real Topic'
    ])

    # Assert 2: Update
    assert result_update.exit_code == 0
    assert "Updated schedule" in result_update.output
    updated_schedule = schedule_manager.get_by_name('cli_managed_schedule')
    assert updated_schedule is not None
    assert updated_schedule.id == schedule.id
    assert updated_schedule.cron_schedule == '*/10 * * * *'
    assert updated_schedule.task_parameters['topic'] == 'New Real Topic'


def test_cli_stop_disables_schedule_real(runner, schedule_manager, test_db_path):
    """
    Integration test for `scheduler stop`: verifies it disables the schedule.
    """
    # Arrange: Create a schedule to be disabled
    schedule = TweetSchedule(name='cli_managed_schedule', cron_schedule='* * * * *', enabled=True)
    schedule_manager.save(schedule)

    pid_file = os.path.join(os.path.dirname(test_db_path), 'test.pid')
    with open(pid_file, 'w') as f:
        f.write('12345')

    # Act
    with patch.dict(conf.cc.module, {"common": {"pid_file": pid_file}}):
        result = runner.invoke(main, ['scheduler', 'stop'])

    # Assert
    assert result.exit_code == 0
    assert "Scheduler stopped" in result.output
    assert "Disabled schedule" in result.output
    updated_schedule = schedule_manager.get_by_name('cli_managed_schedule')
    assert updated_schedule is not None
    assert updated_schedule.enabled is False
    assert not os.path.exists(pid_file)
