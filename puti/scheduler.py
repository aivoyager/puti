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
from typing import Any
from puti.constant.base import Pathh
from puti.logs import logger_factory
import click

lgr = logger_factory.default


class SchedulerDaemon(BaseModel):
    """Handles the daemonization of the Celery Beat scheduler."""
    pidfile: str = Field(default=str(Path.home() / 'puti' / 'scheduler.pid'),
                         description="Path to the scheduler's PID file.")

    def model_post_init(self, __context: Any) -> None:
        """Create the directory for the PID file after initialization."""
        pid_dir = os.path.dirname(self.pidfile)
        os.makedirs(pid_dir, exist_ok=True)

    def _get_pid(self) -> int | None:
        """Read the PID from the PID file."""
        try:
            with open(self.pidfile, 'r') as pf:
                return int(pf.read().strip())
        except (IOError, ValueError):
            return None

    def is_running(self) -> bool:
        """Check if the daemon is currently running."""
        pid = self._get_pid()
        if not pid:
            return False
        
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def start(self):
        """Start the Celery Beat scheduler as a daemon."""
        if self.is_running():
            lgr.warning(f"Scheduler is already running with PID {self._get_pid()}.")
            click.echo(f"Scheduler is already running.")
            return

        lgr.info("Starting Celery Beat scheduler as a daemon...")

        # We use the default Celery Beat scheduler. It is configured in
        # celery_config.py to run our `check_dynamic_schedules` task, which
        # then reads our custom schedule from the database.
        command = [
            'celery', '-A', 'celery_queue.celery_app', 'beat',
            '--loglevel=INFO'
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )

        with open(self.pidfile, 'w') as f:
            f.write(str(process.pid))

        lgr.info(f"Scheduler started with PID: {process.pid}")
        click.echo("Scheduler started")

    def stop(self):
        """Stop the scheduler daemon."""
        pid = self._get_pid()
        if not pid:
            lgr.warning("Scheduler is not running (or PID file not found).")
            click.echo("Scheduler is not running.")
            return

        lgr.info(f"Stopping scheduler with PID: {pid}...")

        try:
            os.killpg(os.getpgid(pid), 15)
        except OSError as e:
            lgr.error(f"Failed to stop scheduler: {e}")
            click.echo(f"Error stopping scheduler: {e}", err=True)
        finally:
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)
            lgr.info("Scheduler stopped and PID file removed.")
            click.echo("Scheduler stopped.")

def cleanup_daemon():
    """A cleanup function to be registered with atexit to ensure the daemon is stopped."""
    daemon = SchedulerDaemon()
    if daemon.is_running():
        daemon.stop()

# Ensure the daemon is stopped on exit, just in case
atexit.register(cleanup_daemon) 