"""
@Author: obstacle
@Time: 26/06/20 11:00
@Description: Handles the daemonization of Celery worker and beat processes.
"""
import os
import sys
import signal
import time
import subprocess
from pathlib import Path
from puti.constant.base import Pathh
from typing import Optional, List, Dict, Any
from puti.logs import logger_factory
from pydantic import BaseModel

lgr = logger_factory.default


class Daemon(BaseModel):
    """Base class for managing daemon processes (worker, beat)."""

    name: str
    pid_file: str
    log_file: str

    def _get_pid_from_file(self) -> Optional[int]:
        """Reads the PID from the PID file."""
        if not os.path.exists(self.pid_file):
            return None
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (IOError, ValueError):
            return None
    
    def is_running(self) -> bool:
        """Checks if the daemon process is currently running."""
        pid = self._get_pid_from_file()
        if not pid:
            return False

        try:
            os.kill(pid, 0)  # not kill, for detect
            return True
        except OSError:
            # Process doesn't exist, clean up stale PID file
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            return False
    
    def get_command(self) -> str:
        """Returns the command to start the daemon. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def start(self, env_command: str = "conda run -n puti") -> bool:
        """Starts the daemon process."""
        # TODO: virtual environment
        if self.is_running():
            lgr.debug(f"{self.name} is already running")
            return True
        
        command = self.get_command()
        full_command = f"{env_command} {command}" if env_command else command
        
        lgr.debug(f"Starting {self.name} with command: {full_command}")
        try:
            subprocess.Popen(
                full_command.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for the process to start and create its PID file
            for _ in range(10):
                time.sleep(1)
                if self.is_running():
                    lgr.info(f"{self.name} started successfully")
                    return True
            
            lgr.error(f"Failed to start {self.name}. Check the log file: {self.log_file}")
            return False
        except Exception as e:
            lgr.error(f"Error starting {self.name}: {str(e)}")
            return False
    
    def stop(self, force: bool = False) -> bool:
        """Stops the daemon process."""
        pid = self._get_pid_from_file()
        if not pid:
            lgr.info(f"{self.name} is not running")
            return True
        
        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            
            # Wait for the process to terminate
            for _ in range(5):
                time.sleep(1)
                if not self.is_running():
                    lgr.info(f"{self.name} stopped successfully")
                    return True
            
            if force:
                lgr.error(f"Failed to stop {self.name} even with SIGKILL")
                return False
            else:
                lgr.warning(f"{self.name} did not stop gracefully, try with --force")
                return False
        except OSError as e:
            lgr.error(f"Error stopping {self.name}: {str(e)}")
            if not self.is_running():  # Process already gone
                return True
            return False
    
    def restart(self, env_command: str = "conda run -n puti") -> bool:
        """Restarts the daemon process."""
        self.stop()
        time.sleep(2)  # Give it time to release resources
        return self.start(env_command)
    
    def get_status(self) -> Dict[str, Any]:
        """Returns the status of the daemon."""
        pid = self._get_pid_from_file()
        running = self.is_running()
        
        return {
            "name": self.name,
            "running": running,
            "pid": pid if running else None,
            "pid_file": self.pid_file,
            "log_file": self.log_file
        }


class WorkerDaemon(Daemon):
    """Manages the Celery worker daemon."""

    def get_command(self) -> str:
        return (
            f"celery -A celery_queue.celery_app worker "
            f"--loglevel=INFO --detach "
            f"--pidfile={self.pid_file} "
            f"--logfile={self.log_file}"
        )


class BeatDaemon(Daemon):
    """Manages the Celery beat daemon."""

    def get_command(self) -> str:
        return (
            f"celery -A celery_queue.celery_app beat "
            f"--loglevel=INFO --detach "
            f"--pidfile={self.pid_file} "
            f"--logfile={self.log_file}"
        )


# For backward compatibility
class SchedulerDaemon(BeatDaemon):
    """Legacy class for backward compatibility with existing code."""
    pass


def ensure_worker_running() -> bool:
    """Ensures that the worker daemon is running."""
    worker = WorkerDaemon(name='worker', pid_file=Pathh.WORKER_PID.val, log_file=Pathh.WORKER_LOG.val)
    if not worker.is_running():
        return worker.start()
    return True


def ensure_beat_running() -> bool:
    """Ensures that the beat daemon is running."""
    beat = BeatDaemon(name='beat', pid_file=Pathh.BEAT_PID.val, log_file=Pathh.BEAT_LOG.val)
    if not beat.is_running():
        return beat.start()
    return True
