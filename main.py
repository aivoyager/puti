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

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from logs import logger_factory
from client.twitter import TwikitClient
from constant import VA
from logs_uvicore import get_uvicorn_log_config

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
    lgr.info('Application started')
    start_server(redis, amqp, celery)
    twitter_client = TwikitClient()
    app.state.twitter_client = twitter_client
    #
    # await twitter_client.save_my_tweet()
    lgr.info('Init twitter client successfully in lifespan')

    yield
    print('clean up')
    # del twitter_client


app = FastAPI(lifespan=lifespan)


@app.get('/client_request')
async def client_request(request: Request):
    # print(request.app.state.twitter_client)
    # return request.app.state.twitter_client
    return 'ok'


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to run the server on")
@click.option("--reload", is_flag=True, help="Enable auto-reload during development")
def run_server(host, port, reload):
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_config=get_uvicorn_log_config(str(VA.ROOT_DIR.val / 'logs' / 'uvicorn'), 'DEBUG')
    )


if __name__ == '__main__':
    run_server()
