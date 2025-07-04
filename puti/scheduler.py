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
import platform
from pathlib import Path
from puti.constant.base import Pathh
from typing import Optional, List, Dict, Any
from puti.logs import logger_factory
from pydantic import BaseModel

lgr = logger_factory.default


def get_current_venv_command() -> Optional[str]:
    """
    Determines the command to run in the current Python virtual environment.
    Supports conda, venv, and poetry.
    Returns the absolute path to the python executable if possible.
    """
    # Check for conda environment
    conda_env_path = os.environ.get('CONDA_PREFIX')
    if conda_env_path:
        python_executable = Path(conda_env_path) / 'bin' / 'python'
        if python_executable.exists():
            return str(python_executable)

    # Check for standard venv
    virtual_env_path = os.environ.get('VIRTUAL_ENV')
    if virtual_env_path:
        python_executable = Path(virtual_env_path) / 'bin' / 'python'
        if python_executable.exists():
            return str(python_executable)

    # If inside an active venv, sys.executable should be the right one
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return sys.executable

    # Fallback for poetry
    try:
        result = subprocess.run(['poetry', 'env', 'info', '-p'], capture_output=True, text=True, check=True)
        venv_path = result.stdout.strip()
        if venv_path:
            python_executable = Path(venv_path) / 'bin' / 'python'
            if python_executable.exists():
                return str(python_executable)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    return "python" # Fallback to just 'python'


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
    
    def start(self, env_command: Optional[str] = "auto") -> bool:
        """Starts the daemon process."""
        if self.is_running():
            lgr.debug(f"{self.name} is already running")
            return True

        if env_command == "auto":
            env_command = get_current_venv_command()

        command = self.get_command()
        
        # If env_command is a python executable, we use it directly.
        # Otherwise, it's a command like 'poetry run'.
        if env_command and Path(env_command).is_file() and 'python' in Path(env_command).name:
            full_command = f"{env_command} -m {command}"
        else:
            full_command = f"{env_command} {command}" if env_command else command

        lgr.debug(f"Starting {self.name} with command: {full_command}")

        # Get the current environment and add the fork safety variable for macOS
        proc_env = os.environ.copy()
        if platform.system() == "Darwin":
            proc_env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
            
        try:
            process = subprocess.Popen(
                full_command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=proc_env
            )

            # Wait for the process to start and create its PID file
            for _ in range(10):
                time.sleep(1)
                if self.is_running():
                    lgr.info(f"{self.name} started successfully")
                    return True

            # If the process failed to start, read stderr
            _, stderr = process.communicate(timeout=1)
            error_message = stderr.strip() if stderr else "No error message captured."
            lgr.error(f"Failed to start {self.name}. Check the log file: {self.log_file}")
            if error_message:
                lgr.error(f"Captured stderr: {error_message}")
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
            f"celery -A puti.celery_queue.celery_app worker "
            f"--loglevel=INFO --detach "
            f"--pidfile={self.pid_file} "
            f"--logfile={self.log_file}"
        )


class BeatDaemon(Daemon):
    """Manages the Celery beat daemon."""

    def get_command(self) -> str:
        return (
            f"celery -A puti.celery_queue.celery_app beat "
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
