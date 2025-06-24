"""
@Author: obstacle
@Time: 20/01/25 11:29
@Description:  
"""
import time
import uvicorn
import click
import os
import sys
import subprocess
import socket
import psutil
import platform

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from puti.logs import logger_factory
from api.chat import chat_router

lgr = logger_factory.default
current_os = platform.system()


def is_process_running(keyword):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if keyword in cmdline:
                return True
        except Exception:
            continue
    return False


def check_celery_worker_and_beat():
    worker_cmd = 'celery -A celery_queue.celery_app worker'
    beat_cmd = 'celery -A celery_queue.celery_app beat'
    worker_running = is_process_running(worker_cmd)
    beat_running = is_process_running(beat_cmd)

    if not worker_running:
        subprocess.Popen([
            'celery', '-A', 'celery_queue.celery_app', 'worker', '--loglevel=info', '--concurrency=4'
        ])
        lgr.info('[Automatically trying to start Celery Worker]')
    else:
        lgr.info('[Celery Worker] Already running')

    if not beat_running:
        subprocess.Popen([
            'celery', '-A', 'celery_queue.celery_app', 'beat', '--loglevel=info'
        ])
        lgr.info('[Automatically trying to start Celery Beat]')
    else:
        lgr.info('[Celery Beat] Already running')


def init_services():
    check_celery_worker_and_beat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    lgr.debug('application started')

    init_services()
    yield
    lgr.debug('clean up')
    # Release/close related resources
    try:
        # Only close resources that were started in lifespan and mounted to app.state
        # Close Twitter client (if any)
        twitter_client = getattr(app.state, 'twitter_client', None)
        if twitter_client:
            try:
                twitter_client.close()
                lgr.info("[Twitter Client] Closed.")
            except Exception as e:
                lgr.warning(f"[Twitter Client] Close exception: {e}")
        # Close database connection (if any)
        db = getattr(app.state, 'db', None)
        if db:
            try:
                db.close()
                lgr.info("[DB] Closed.")
            except Exception as e:
                lgr.warning(f"[DB] Close exception: {e}")
        # Close logger (if any)
        try:
            logger_factory.default.handlers.clear()
            lgr.info("[Logger] Handler cleared.");
        except Exception as e:
            lgr.warning(f"[Logger] Handler clear exception: {e}")
    except Exception as e:
        lgr.error(f"[Lifespan cleanup] Resource release exception: {e}")


sub_app = FastAPI(
    title='puti',
    description='Puti API for readers',
    version='1.0.0',
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url='/openapi.json',
)
app = FastAPI(lifespan=lifespan)
app.mount('/ai/puti', sub_app)
sub_app.include_router(chat_router, prefix='/chat', tags=['chat'])


@sub_app.get('/client_request')
async def client_request(request: Request):
    return 'ok'


@click.group()
def cli():
    """Puti command line tools."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to run the server on")
@click.option("--reload", is_flag=True, help="Enable auto-reload during development")
@click.option('--loop', default='asyncio')
def server(host, port, reload, loop):
    """Run the FastAPI server."""
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        # log_config=get_uvicorn_log_config(str(root_dir() / 'logs' / 'uvicorn'), 'DEBUG'),
        loop=loop
    )


@click.group()
def scheduler():
    """
    Manage tweet scheduler operations.
    
    This command group provides tools to:
    
    1. Start/stop the scheduler daemon
    2. View task status and schedule information
    """
    pass


@scheduler.command()
@click.option('--start-tasks/--no-start-tasks', default=True, 
              help="Whether to activate all enabled tasks when starting the daemon")
def start(start_tasks):
    """Start the scheduler daemon."""
    from puti.scheduler import SchedulerDaemon
    daemon = SchedulerDaemon()
    daemon.start(activate_tasks=start_tasks)


@scheduler.command()
def stop():
    """Stop the scheduler daemon."""
    from puti.scheduler import SchedulerDaemon
    daemon = SchedulerDaemon()
    daemon.stop()


@scheduler.command()
def status():
    """Check if the scheduler daemon is running."""
    from puti.scheduler import SchedulerDaemon
    daemon = SchedulerDaemon()
    if daemon.is_running():
        pid = daemon._get_pid()
        click.echo(f"Scheduler is running with PID {pid}")
    else:
        click.echo("Scheduler is not running")


# Add scheduler command group to main CLI
cli.add_command(scheduler)


if __name__ == '__main__':
    cli()
