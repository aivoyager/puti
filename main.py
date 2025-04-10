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
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Depends
from contextlib import asynccontextmanager
from logs import logger_factory
from logs_uvicore import get_uvicorn_log_config
from utils.path import root_dir
from client.twitter.twitter_client import TwikitClient
from api.chat import chat_router

lgr = logger_factory.default


# TODO move to supervisor later...
def redis():
    redis_command = ['redis-server', '--port', '6379']
    subprocess.run(redis_command)


def amqp():
    amqp_stop_command = ['brew', 'services', 'stop', 'rabbitmq']
    amqp_command = ['brew', 'services', 'start', 'rabbitmq']  # macos
    # amqp_command = ['sudo systemctl start rabbitmq-server']  # Ubuntu
    subprocess.run(amqp_stop_command)
    subprocess.run(amqp_command)


def celery():
    celery_command = ['celery', '-A', 'puti.celery_queue.celery_app', 'worker', '--port', 5676, '--loglevel=info']
    celery_beat = ['celery', '-A', 'puti.celery_queue.celery_app', 'beat', '--port', 5677, '--loglevel=info']
    celery_flower = ['celery', '-A', 'puti.celery_queue.celery_app', 'flower', '--port', 5678, '--persistent', True, '--db', 'flower', 'basic_auth', 'admin:123']
    subprocess.Popen(celery_command)
    subprocess.Popen(celery_beat)
    subprocess.Popen(celery_flower)


def start_server(*services):
    for service in services:
        thread = threading.Thread(target=service)
        thread.daemon = True
        thread.start()
        if service.__name__ == 'amqp':
            time.sleep(2)
        lgr.info(f'===> {service.__name__} server started...')


@asynccontextmanager
async def lifespan(app: FastAPI):
    lgr.debug('application started')
    # start_server(redis, amqp, celery)

    # Don't init twitter client if there is no need, which may blocked your account
    # twitter_client = TwikitClient()
    # app.state.twitter_client = twitter_client
    # lgr.info('Init twitter client successfully in lifespan')

    yield
    # print('clean up')
    lgr.debug('clean up')
    # del twitter_client


sub_app = FastAPI(
    lifespan=lifespan,
    title='puti',
    description='Puti API for readers',
    version='1.0.0',
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url='/openapi.json',
)
app = FastAPI()
app.mount('/ai/puti', sub_app)
sub_app.include_router(chat_router, prefix='/chat', tags=['chat'])


@sub_app.get('/client_request')
async def client_request(request: Request):
    # print(request.app.state.twitter_client)
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
