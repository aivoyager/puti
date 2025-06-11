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


@click.command()
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to run the server on")
@click.option("--reload", is_flag=True, help="Enable auto-reload during development")
@click.option('--loop', default='asyncio')
def run_server(host, port, reload, loop):
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        # log_config=get_uvicorn_log_config(str(root_dir() / 'logs' / 'uvicorn'), 'DEBUG'),
        loop=loop
    )


if __name__ == '__main__':
    run_server()
