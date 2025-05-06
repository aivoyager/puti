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
import socket
import psutil
import platform
import kombu
import redis as redis_py

from gevent import monkey

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf import celery_config
from fastapi import FastAPI, Request, Depends
from contextlib import asynccontextmanager
from logs import logger_factory
from logs_uvicore import get_uvicorn_log_config
from utils.path import root_dir
from client.twitter.twitter_client import TwikitClient
from api.chat import chat_router

lgr = logger_factory.default
current_os = platform.system()


def redis():
    redis_command = ['redis-server', '--port', '6379']
    subprocess.Popen(redis_command)


def amqp():
    amqp_stop_command = ['brew', 'services', 'stop', 'rabbitmq']
    if current_os == 'Darwin':
        amqp_command = ['brew', 'services', 'start', 'rabbitmq']  # macos
    elif current_os == 'Linux':
        amqp_command = ['sudo systemctl start rabbitmq-server']  # Ubuntu
    else:
        lgr.error(f'Unsupported OS {current_os}')
        raise Exception('Unsupported OS')
    subprocess.Popen(amqp_stop_command)
    time.sleep(1)
    subprocess.Popen(amqp_command)
    time.sleep(1)
    # 增加端口检测，确保RabbitMQ服务已启动
    for i in range(20):
        time.sleep(1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1)
            sock.connect(('127.0.0.1', 5672))
            lgr.info('[RabbitMQ] Service started and listening on 127.0.0.1:5672')
            sock.close()
            break
        except Exception as e:
            amqp_command = ['brew', 'services', 'start', 'rabbitmq']
            subprocess.Popen(amqp_command)
            lgr.info(f'[RabbitMQ] Waiting for service to start...({i+1}/20): {e}')
        finally:
            sock.close()
    else:
        lgr.error('[RabbitMQ] Startup timeout, port not listening')


def celery():
    celery_command = ['celery', '-A', 'puti.celery_queue.celery_app', 'worker', '--port', 5676, '--loglevel=info']
    celery_beat = ['celery', '-A', 'puti.celery_queue.celery_app', 'beat', '--port', 5677, '--loglevel=info']
    celery_flower = ['celery', '-A', 'puti.celery_queue.celery_app', 'flower', '--port', 5678, '--persistent', True,
                     '--db', 'flower', 'basic_auth', 'admin:123']
    subprocess.Popen(celery_command)
    subprocess.Popen(celery_beat)
    subprocess.Popen(celery_flower)
    time.sleep(2)


def init_services():
    """
    统一检测并启动 Redis、AMQP（RabbitMQ）、Celery Worker/Beat 服务
    """
    broker_url = celery_config.broker_url
    # 启动 Redis（仅本地开发环境需要）
    if current_os in ['Windows', 'Darwin']:
        try:
            redis_running = any("redis-server" in p.name() for p in psutil.process_iter())
            if not redis_running:
                lgr.info("[start Redis service in advance]")
                redis()
                time.sleep(2)
        except Exception as psutil_error:
            lgr.warning(f"[Redis] process check failed: {psutil_error}")
    # 启动 RabbitMQ（如果使用 AMQP）
    if broker_url.startswith('amqp'):
        lgr.info("[Auto trying start RabbitMQ service]")
        amqp()
        # 端口检测已在amqp函数内实现，无需额外等待
    # 启动 Celery Worker/Beat
    check_celery_worker_and_beat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    lgr.debug('application started')
    lgr.debug(socket.socket)

    # Unified service initialization
    init_services()

    # Do not initialize twitter client when not needed to avoid account ban
    # twitter_client = TwikitClient()
    # app.state.twitter_client = twitter_client
    # lgr.info('Init twitter client successfully in lifespan')
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


# 删除 check_broker_health_and_auto_start 相关函数和调用
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


if __name__ == '__main__':
    run_server()
