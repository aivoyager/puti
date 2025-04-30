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
import kombu

lgr = logger_factory.default


# TODO move to supervisor later...
def redis():
    redis_command = ['redis-server', '--port', '6379']
    subprocess.Popen(redis_command)


def amqp():
    amqp_stop_command = ['brew', 'services', 'stop', 'rabbitmq']
    amqp_command = ['brew', 'services', 'start', 'rabbitmq']  # macos
    # amqp_command = ['sudo systemctl start rabbitmq-server']  # Ubuntu
    subprocess.Popen(amqp_stop_command)
    subprocess.Popen(amqp_command)


def celery():
    celery_command = ['celery', '-A', 'puti.celery_queue.celery_app', 'worker', '--port', 5676, '--loglevel=info']
    celery_beat = ['celery', '-A', 'puti.celery_queue.celery_app', 'beat', '--port', 5677, '--loglevel=info']
    celery_flower = ['celery', '-A', 'puti.celery_queue.celery_app', 'flower', '--port', 5678, '--persistent', True,
                     '--db', 'flower', 'basic_auth', 'admin:123']
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
    
    # 首先确保Redis服务启动
    try:
        import psutil
    except ImportError:
        print("[自动安装psutil依赖]")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
        import psutil
        
    try:
        redis_running = any("redis-server" in p.name() for p in psutil.process_iter())
        if not redis_running:
            lgr.info("[优先启动 Redis 服务]")
            redis()
            time.sleep(2)  # 等待Redis完全启动
    except Exception as psutil_error:
        lgr.warning(f"[Redis] 进程检查失败: {psutil_error}")
    
    # 然后确保RabbitMQ服务启动
    if not check_broker_health_and_auto_start():
        lgr.error("[警告] Celery broker 未启动或无法连接，请检查RabbitMQ服务！")
        time.sleep(3)  # 等待RabbitMQ完全启动
    
    # 最后启动其他服务
    check_celery_worker_and_beat()
    # start_server(redis, amqp, celery)
    # 不需要时不初始化twitter client，避免被封号
    # twitter_client = TwikitClient()
    # app.state.twitter_client = twitter_client
    # lgr.info('Init twitter client successfully in lifespan')
    yield
    lgr.debug('clean up')
    # 释放/关闭相关资源
    try:
        # 仅关闭在 lifespan 启动并挂载到 app.state 的资源
        # 关闭 Twitter 客户端（如果有）
        twitter_client = getattr(app.state, 'twitter_client', None)
        if twitter_client:
            try:
                twitter_client.close()
                lgr.info("[Twitter Client] 已关闭。")
            except Exception as e:
                lgr.warning(f"[Twitter Client] 关闭异常: {e}")
        # 关闭数据库连接（如有）
        db = getattr(app.state, 'db', None)
        if db:
            try:
                db.close()
                lgr.info("[DB] 已关闭。")
            except Exception as e:
                lgr.warning(f"[DB] 关闭异常: {e}")
        # 关闭日志（如有）
        try:
            logger_factory.default.handlers.clear()
            lgr.info("[Logger] 已清理 handler。");
        except Exception as e:
            lgr.warning(f"[Logger] 清理 handler 异常: {e}")
    except Exception as e:
        lgr.error(f"[Lifespan 清理] 资源释放异常: {e}")
    # del twitter_client


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


# ===================== Celery Broker 启动相关 =====================
def check_broker_health_and_auto_start():
    from conf import celery_config
    broker_url = celery_config.broker_url
    result_backend = celery_config.result_backend
    max_retries = 5  # 增加重试次数
    retry_delay = 3  # 延长重试间隔
    
    # 检查broker和result_backend是否都可用
    for attempt in range(1, max_retries + 1):
        broker_ok = False
        backend_ok = False

        # 检查broker连接
        try:
            conn = kombu.Connection(broker_url)
            conn.connect()
            conn.release()
            broker_ok = True
            lgr.info(f"[Celery Broker] {broker_url} 连接成功")
        except Exception as e:
            lgr.error(f"[Celery Broker] {broker_url} 连接失败 (尝试 {attempt}/{max_retries}): {e}")

            if broker_url.startswith('amqp'):
                lgr.info("[自动尝试启动 RabbitMQ 服务]")
                amqp()
                time.sleep(5)  # 给RabbitMQ更多启动时间
            elif broker_url.startswith('redis'):
                lgr.info("[自动尝试启动 Redis 服务]")
                redis()
                time.sleep(2)  # 给Redis启动时间
                try:
                    import psutil
                    redis_running = any("redis-server" in p.info().get('name', '')
                                      for p in psutil.process_iter(['name']))
                    if not redis_running:
                        lgr.error("[Redis] 服务启动失败，请检查Redis安装和配置")
                except Exception as psutil_error:
                    lgr.warning(f"[Redis] 进程检查失败: {psutil_error}")

        # 检查result_backend连接
        try:
            if result_backend.startswith('redis'):
                import redis as redis_py
                r = redis_py.from_url(result_backend)
                r.ping()
                backend_ok = True
                lgr.info(f"[Result Backend] {result_backend} 连接成功")
            elif result_backend.startswith('amqp'):
                backend_conn = kombu.Connection(result_backend)
                backend_conn.connect()
                backend_conn.release()
                backend_ok = True
                lgr.info(f"[Result Backend] {result_backend} 连接成功")
        except Exception as e:
            lgr.error(f"[Result Backend] {result_backend} 连接失败 (尝试 {attempt}/{max_retries}): {e}")

            if result_backend.startswith('redis') and not broker_url.startswith('redis'):
                lgr.info("[自动尝试启动 Redis 服务(用于结果后端)]")
                redis()
                time.sleep(2)

        if broker_ok and backend_ok:
            return True

        if attempt < max_retries:
            time.sleep(retry_delay)
            continue

        lgr.error(f"[Celery Broker] 经过 {max_retries} 次尝试后仍然连接失败")
        return False


# ===================== Celery Worker/Beat 检查与启动 =====================
def is_process_running(keyword):
    import psutil
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
        lgr.info('[自动尝试启动 Celery Worker]')
    else:
        lgr.info('[Celery Worker] 已在运行')

    if not beat_running:
        subprocess.Popen([
            'celery', '-A', 'celery_queue.celery_app', 'beat', '--loglevel=info'
        ])
        lgr.info('[自动尝试启动 Celery Beat]')
    else:
        lgr.info('[Celery Beat] 已在运行')


# ===================== Redis/RabbitMQ 启动命令 =====================
# def redis():
#     redis_command = ['redis-server', '--port', '6379']
#     subprocess.run(redis_command)

# def amqp():
#     amqp_stop_command = ['brew', 'services', 'stop', 'rabbitmq']
#     amqp_command = ['brew', 'services', 'start', 'rabbitmq']
#     subprocess.run(amqp_stop_command)
#     subprocess.run(amqp_command)

# def celery():
#     celery_command = ['celery', '-A', 'puti.celery_queue.celery_app', 'worker', '--port', 5676, '--loglevel=info']
#     celery_beat = ['celery', '-A', 'puti.celery_queue.celery_app', 'beat', '--port', 5677, '--loglevel=info']
#     celery_flower = ['celery', '-A', 'puti.celery_queue.celery_app', 'flower', '--port', 5678, '--persistent', True,
#                      '--db', 'flower', 'basic_auth', 'admin:123']
#     subprocess.Popen(celery_command)
#     subprocess.Popen(celery_beat)
#     subprocess.Popen(celery_flower)

# ===================== 多服务并发启动工具 =====================
# def start_server(*services):
#     for service in services:
#         thread = threading.Thread(target=service)
#         thread.daemon = True
#         thread.start()
#         if service.__name__ == 'amqp':
#             time.sleep(2)
#         lgr.info(f'===> {service.__name__} server started...')


if __name__ == '__main__':
    run_server()
