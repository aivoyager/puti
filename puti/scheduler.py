"""
@Author: obstacle
@Time: 26/06/20 11:00
@Description: Handles the daemonization of the Celery Beat scheduler.
"""
import os
import sys
import atexit
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Optional
from puti.constant.base import Pathh
from puti.conf.config import conf
from puti.logs import logger_factory
import click

lgr = logger_factory.default


def get_default_log_dir():
    """Reads the log directory from the global config, with a fallback."""
    try:
        return Path(conf.cc.module['common']['log_dir'])
    except (KeyError, AttributeError):
        return Path.home() / 'puti' / 'logs'


class SchedulerDaemon(BaseModel):
    """Handles the daemonization of the Celery Beat scheduler."""
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize database managers
        from puti.db.base_manager import BaseManager
        from puti.db.model.system import SystemSetting
        self.setting_manager = BaseManager(model_type=SystemSetting)

    def model_post_init(self, __context: Any) -> None:
        """Initialize any resources needed by the daemon."""
        log_dir = get_default_log_dir()
        os.makedirs(log_dir, exist_ok=True)

    def _get_pid(self) -> int | None:
        """Read the PID from the database."""
        setting = self.setting_manager.get_one(where_clause="name = 'scheduler_pid'")
        if setting:
            try:
                return int(setting.value)
            except (ValueError, TypeError):
                return None
        return None

    def _set_pid(self, pid: int) -> None:
        """Store the PID in the database."""
        from puti.db.model.system import SystemSetting
        setting = self.setting_manager.get_one(where_clause="name = 'scheduler_pid'")
        if setting:
            self.setting_manager.update(setting.id, {"value": str(pid)})
        else:
            setting = SystemSetting(
                name="scheduler_pid",
                value=str(pid),
                description="PID of the currently running Celery Beat scheduler daemon"
            )
            self.setting_manager.save(setting)

    def _clear_pid(self) -> None:
        """Remove the stored PID from the database."""
        setting = self.setting_manager.get_one(where_clause="name = 'scheduler_pid'")
        if setting:
            self.setting_manager.delete(setting.id, soft_delete=False)

    def is_running(self) -> bool:
        """Check if the daemon is currently running."""
        pid = self._get_pid()
        if not pid:
            return False
        
        try:
            os.kill(pid, 0)
        except OSError:
            # Process doesn't exist or we don't have permission to send signals
            # Clean up the stale PID record
            self._clear_pid()
            return False
        else:
            return True

    def start(self, activate_tasks: bool = True):
        """
        Start the Celery Beat scheduler as a daemon.
        
        Args:
            activate_tasks: Whether to activate all enabled schedules when starting
        """
        if self.is_running():
            lgr.warning(f"Scheduler is already running with PID {self._get_pid()}.")
            click.echo(f"Scheduler is already running.")
            return

        lgr.info("Starting Celery Beat scheduler as a daemon...")
        click.echo("Starting scheduler daemon in background...")
        
        # Activate all enabled schedules if requested
        if activate_tasks:
            self._ensure_enabled_schedules_run()

        # Use the shared application config directory for logs
        log_dir = get_default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        # Combine stdout and stderr into a single log file for easier monitoring
        log_path = log_dir / 'scheduler_beat.log'

        # We use the default Celery Beat scheduler. It is configured in
        # celery_config.py to run our `check_dynamic_schedules` task, which
        # then reads our custom schedule from the database.
        command = [
            'celery', '-A', 'celery_queue.celery_app', 'beat',
            '--loglevel=INFO'
        ]

        log_file = open(log_path, 'a')

        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT, # Redirect stderr to stdout
            preexec_fn=os.setsid
        )
        
        # The file descriptor is duplicated for the child process, so the parent
        # should close its copy.
        log_file.close()

        # Store the PID in the database
        self._set_pid(process.pid)

        lgr.info(f"Scheduler started with PID: {process.pid}")
        click.echo("Scheduler started")
        click.echo(f"  - PID: {process.pid}")
        click.echo(f"  - Log file: {log_path.resolve()}")
        
        # Get list of enabled tasks for display
        from puti.db.schedule_manager import ScheduleManager
        manager = ScheduleManager()
        enabled_tasks = manager.get_active_schedules()
        
        if enabled_tasks:
            click.echo(f"  - Enabled tasks: {len(enabled_tasks)}")
            for task in enabled_tasks[:5]:  # Show only first 5 to avoid clutter
                click.echo(f"      - {task.name}")
            if len(enabled_tasks) > 5:
                click.echo(f"      - ... and {len(enabled_tasks) - 5} more")
        else:
            click.echo("  - No enabled tasks")

    def _ensure_enabled_schedules_run(self):
        """Makes sure that all active schedules in the database are running."""
        # Trigger an immediate check of all enabled schedules
        from celery_queue.tasks import check_dynamic_schedules
        check_dynamic_schedules.delay()
        lgr.info("Triggered an immediate check of all enabled schedules.")
        
    def get_active_schedules(self):
        """Returns all active schedules from the database."""
        from puti.db.schedule_manager import ScheduleManager
        
        manager = ScheduleManager()
        return manager.get_active_schedules()
        
    def get_running_schedules(self):
        """Returns all currently running schedules from the database."""
        from puti.db.schedule_manager import ScheduleManager
        
        manager = ScheduleManager()
        return manager.get_running_schedules()

    def stop(self):
        """Stop the scheduler daemon."""
        pid = self._get_pid()
        if not pid:
            lgr.warning("Scheduler is not running (or PID not found in database).")
            click.echo("Scheduler is not running.")
            return

        lgr.info(f"Stopping scheduler with PID: {pid}...")

        try:
            # Attempt to kill the process group associated with the PID
            os.killpg(os.getpgid(pid), 15)
        except ProcessLookupError:
            # This is not a fatal error. It simply means the process with the given PID
            # was not found. It's safe to assume it's already stopped.
            lgr.warning(f"Process with PID {pid} not found, likely already stopped. Cleaning up PID record.")
        except OSError as e:
            # Handle other, unexpected OS errors
            lgr.error(f"Failed to stop scheduler: {e}")
            click.echo(f"Error stopping scheduler: {e}", err=True)
        finally:
            # Always clear the PID from the database
            self._clear_pid()
            
            # Also mark all running tasks as stopped
            from puti.db.schedule_manager import ScheduleManager
            manager = ScheduleManager()
            running_schedules = manager.get_running_schedules()
            
            for schedule in running_schedules:
                manager.update_schedule(schedule.id, is_running=False, pid=None)
                lgr.info(f"Marked task '{schedule.name}' (ID: {schedule.id}) as stopped")
                
            lgr.info("Scheduler stopped and PID record removed.")
            click.echo("Scheduler stopped.")
            if running_schedules:
                click.echo(f"  - {len(running_schedules)} running tasks were marked as stopped")


def cleanup_daemon():
    """A cleanup function to be registered with atexit to ensure the daemon is stopped."""
    daemon = SchedulerDaemon()
    if daemon.is_running():
        daemon.stop()

# Ensure the daemon is stopped on exit, just in case
atexit.register(cleanup_daemon) 