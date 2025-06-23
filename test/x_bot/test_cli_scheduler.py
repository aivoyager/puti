"""
@Author: obstacle
@Time: 28/06/20 10:00
@Description: Unit tests for the CLI scheduler commands using mocks.
"""
import pytest
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

@patch('puti.db.base_manager.BaseManager')
def test_cli_set_creates_schedule(mock_manager_class, runner):
    """Unit test for `scheduler set`: verifies it calls the manager to create a schedule."""
    # Arrange
    mock_manager_instance = MagicMock()
    # Simulate no schedule exists
    mock_manager_instance.get_all.return_value = []
    mock_manager_class.return_value = mock_manager_instance

    # Act
    result = runner.invoke(main, [
        'scheduler', 'set',
        'test_schedule',
        '* * * * *',
        '--topic', 'Mocked Topic'
    ])

    # Assert
    assert result.exit_code == 0
    assert mock_manager_instance.get_all.called
    mock_manager_instance.save.assert_called_once()
    saved_schedule = mock_manager_instance.save.call_args[0][0]
    assert saved_schedule.name == 'test_schedule'
    assert saved_schedule.cron_schedule == '* * * * *'
    assert saved_schedule.params['topic'] == 'Mocked Topic'


@patch('puti.db.base_manager.BaseManager')
def test_cli_set_updates_schedule(mock_manager_class, runner):
    """Unit test for `scheduler set`: verifies it calls the manager to update a schedule."""
    # Arrange
    existing_schedule = TweetSchedule(id=1, name='test_schedule', cron_schedule='old')
    mock_manager_instance = MagicMock()
    mock_manager_instance.get_all.return_value = [existing_schedule]
    mock_manager_class.return_value = mock_manager_instance

    # Act
    result = runner.invoke(main, [
        'scheduler', 'set',
        'test_schedule',
        '*/5 * * * *',
        '--topic', 'Updated Topic'
    ])

    # Assert
    assert result.exit_code == 0
    assert mock_manager_instance.get_all.called
    mock_manager_instance.update.assert_called_once()
    # Check that the update includes the right parameters
    update_id, updates = mock_manager_instance.update.call_args[0]
    assert update_id == 1
    assert updates["cron_schedule"] == '*/5 * * * *'
    assert updates["params"]["topic"] == 'Updated Topic'
    assert updates["enabled"] is True


@patch('puti.scheduler.SchedulerDaemon')
def test_cli_start_daemon(mock_daemon_class, runner):
    """Unit test for `scheduler start`: verifies it calls the daemon."""
    # Arrange
    mock_daemon_instance = MagicMock()
    mock_daemon_class.return_value = mock_daemon_instance

    # Act
    result = runner.invoke(main, ['scheduler', 'start'])
    
    # Assert
    assert result.exit_code == 0
    mock_daemon_instance.start.assert_called_once()


@patch('puti.scheduler.SchedulerDaemon')
@patch('puti.db.base_manager.BaseManager')
def test_cli_stop_disables_and_stops(mock_manager_class, mock_daemon_class, runner):
    """Unit test for `scheduler stop`: verifies it disables schedules and stops the daemon."""
    # Arrange
    mock_schedule = MagicMock()
    mock_schedule.id = 1
    
    mock_manager_instance = MagicMock()
    mock_manager_instance.get_all.return_value = [mock_schedule]
    mock_manager_class.return_value = mock_manager_instance
    
    mock_daemon_instance = MagicMock()
    mock_daemon_class.return_value = mock_daemon_instance

    # Act
    result = runner.invoke(main, ['scheduler', 'stop'])
    
    # Assert
    assert result.exit_code == 0
    mock_manager_instance.update.assert_called_once_with(1, {"enabled": False})
    mock_daemon_instance.stop.assert_called_once()


@patch('puti.scheduler.SchedulerDaemon')
def test_cli_status_command(mock_daemon_class, runner):
    """Unit test for `scheduler status`: verifies it reports correct status."""
    # Arrange - Running
    mock_daemon_instance = MagicMock()
    mock_daemon_instance.is_running.return_value = True
    mock_daemon_instance._get_pid.return_value = 12345
    mock_daemon_class.return_value = mock_daemon_instance

    # Act
    result = runner.invoke(main, ['scheduler', 'status'])
    
    # Assert
    assert result.exit_code == 0
    assert "Running" in result.output
    assert "12345" in result.output
    
    # Arrange - Not Running
    mock_daemon_instance.is_running.return_value = False
    
    # Act
    result = runner.invoke(main, ['scheduler', 'status'])
    
    # Assert
    assert result.exit_code == 0
    assert "Stopped" in result.output


@patch('puti.db.base_manager.BaseManager')
def test_cli_list_command(mock_manager_class, runner):
    """Unit test for `scheduler list`: verifies it lists schedules correctly."""
    # Arrange
    from datetime import datetime
    
    mock_manager_instance = MagicMock()
    mock_schedule = MagicMock()
    mock_schedule.id = 1
    mock_schedule.name = "test_schedule"
    mock_schedule.cron_schedule = "* * * * *"
    mock_schedule.next_run = datetime.now()
    mock_schedule.last_run = datetime.now()
    mock_schedule.enabled = True
    mock_schedule.params = {"topic": "Test Topic"}
    
    mock_manager_instance.get_all.return_value = [mock_schedule]
    mock_manager_class.return_value = mock_manager_instance
    
    # Act
    result = runner.invoke(main, ['scheduler', 'list'])
    
    # Assert
    assert result.exit_code == 0
    assert "test_schedule" in result.output
    assert "Enabled" in result.output
    
    # Test --all flag
    result = runner.invoke(main, ['scheduler', 'list', '--all'])
    assert result.exit_code == 0
    mock_manager_instance.get_all.assert_called_with(where_clause="")


@patch('puti.db.base_manager.BaseManager')
def test_cli_inspect_command(mock_manager_class, runner):
    """Unit test for `scheduler inspect`: verifies it shows detailed schedule info."""
    # Arrange
    from datetime import datetime, timedelta
    
    mock_manager_instance = MagicMock()
    mock_schedule = MagicMock()
    mock_schedule.id = 1
    mock_schedule.name = "test_schedule"
    mock_schedule.cron_schedule = "* * * * *"
    mock_schedule.next_run = datetime.now() + timedelta(minutes=10)
    mock_schedule.last_run = datetime.now() - timedelta(minutes=5)
    mock_schedule.enabled = True
    mock_schedule.params = {"topic": "Test Topic"}
    mock_schedule.created_at = datetime.now() - timedelta(days=1)
    mock_schedule.updated_at = datetime.now() - timedelta(hours=1)
    
    mock_manager_instance.get_by_id.return_value = mock_schedule
    mock_manager_class.return_value = mock_manager_instance
    
    # Act
    result = runner.invoke(main, ['scheduler', 'inspect', '1'])
    
    # Assert
    assert result.exit_code == 0
    assert "test_schedule" in result.output
    assert "Enabled" in result.output
    assert "Test Topic" in result.output
    
    # Test for non-existent schedule
    mock_manager_instance.get_by_id.return_value = None
    result = runner.invoke(main, ['scheduler', 'inspect', '999'])
    assert result.exit_code == 0
    assert "not found" in result.output


# --- Integration Tests ---

@pytest.fixture
def test_db_path(tmp_path):
    """Provides a temporary database path for integration tests."""
    db_path = str(tmp_path / "test_cli.sqlite")
    # Patch the config *before* the schedule_manager fixture runs
    with patch.dict(conf.cc.module, {"db": {"sqlite": {"path": db_path}}}):
        yield db_path


@pytest.fixture
def schedule_manager(test_db_path):
    """Provides a BaseManager for the TweetSchedule model."""
    from puti.db.base_manager import BaseManager
    from puti.db.model.task.bot_task import TweetSchedule

    # The db_path is already patched in the config
    manager = BaseManager(model_type=TweetSchedule)
    manager.db_operator.execute("DELETE FROM tweet_schedules")
    return manager


def get_pid_from_db(manager) -> int | None:
    """Helper to read the scheduler PID from the database."""
    pid_setting = manager.get_one(where_clause="name = 'scheduler_pid'")
    return int(pid_setting.value) if pid_setting else None


@pytest.fixture
def setting_manager(test_db_path):
    """Provides a BaseManager for the SystemSetting model."""
    from puti.db.base_manager import BaseManager
    from puti.db.model.system import SystemSetting
    manager = BaseManager(model_type=SystemSetting)
    manager.db_operator.execute("DELETE FROM system_settings")
    return manager


def test_cli_set_creates_and_updates_schedule_real(runner, schedule_manager, test_db_path):
    """
    Integration test for `scheduler set`: verifies it creates and then updates a schedule.
    """
    # Act 1: Create the schedule
    result_create = runner.invoke(main, [
        'scheduler', 'set',
        'cli_test_schedule',
        '* * * * *',
        '--topic', 'Real Topic'
    ])

    # Assert 1: Creation
    assert result_create.exit_code == 0
    assert "Created tweet schedule" in result_create.output
    
    schedules = schedule_manager.get_all(where_clause="name = ?", params=('cli_test_schedule',))
    assert len(schedules) == 1
    schedule = schedules[0]
    assert schedule.cron_schedule == '* * * * *'
    assert schedule.params['topic'] == 'Real Topic'
    assert schedule.enabled is True

    # Act 2: Update the schedule
    result_update = runner.invoke(main, [
        'scheduler', 'set',
        'cli_test_schedule',
        '*/10 * * * *',
        '--topic', 'New Real Topic'
    ])

    # Assert 2: Update
    assert result_update.exit_code == 0
    assert "Updated tweet schedule" in result_update.output
    
    schedules = schedule_manager.get_all(where_clause="name = ?", params=('cli_test_schedule',))
    assert len(schedules) == 1
    updated_schedule = schedules[0]
    assert updated_schedule.id == schedule.id
    assert updated_schedule.cron_schedule == '*/10 * * * *'
    assert updated_schedule.params['topic'] == 'New Real Topic'


def test_cli_start_real(runner, setting_manager):
    """
    Integration test for `scheduler start`: verifies it starts the daemon
    and records the PID in the database.
    """
    try:
        # Act
        result = runner.invoke(main, ['scheduler', 'start'])

        # Assert Start
        assert result.exit_code == 0
        assert "Scheduler started" in result.output
        pid = get_pid_from_db(setting_manager)
        assert pid is not None
        assert pid > 0

    finally:
        # Cleanup
        runner.invoke(main, ['scheduler', 'stop'])
        assert get_pid_from_db(setting_manager) is None


def test_cli_stop_disables_schedule_real(runner, schedule_manager, setting_manager):
    """
    Integration test for `scheduler stop`: verifies it disables the schedule
    and removes the PID from the database.
    """
    from puti.db.model.system import SystemSetting
    
    # Arrange
    schedule = TweetSchedule(name='cli_managed_schedule', cron_schedule='* * * * *', enabled=True)
    schedule_manager.save(schedule)
    # Manually create a fake PID in the DB for the test
    setting_manager.save(SystemSetting(name='scheduler_pid', value='12345'))

    # Act
    result = runner.invoke(main, ['scheduler', 'stop'])

    # Assert
    assert result.exit_code == 0
    assert "Scheduler stopped" in result.output
    
    # Check that all schedules were disabled
    schedules = schedule_manager.get_all(where_clause="name = ?", params=('cli_managed_schedule',))
    assert len(schedules) == 1
    updated_schedule = schedules[0]
    assert updated_schedule.enabled is False
    
    # Check that the PID was removed
    assert get_pid_from_db(setting_manager) is None
