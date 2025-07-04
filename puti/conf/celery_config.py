"""
@Author: obstacle
@Time: 20/01/25 15:45
@Description:  
"""
import platform
from datetime import timedelta
import os
from celery.schedules import crontab
from kombu import Queue, Exchange
from typing import Dict, Any, List

from puti.conf.celery_private_conf import CeleryPrivateConfig

c = CeleryPrivateConfig()

# broker_url = 'redis://127.0.0.1:6379/0'
# if platform.system().lower() == 'linux':
broker_url = c.BROKER_URL
# else:
#     broker_url = 'amqp://guest:guest@localhost//'
result_backend = c.RESULT_BACKEND_URL
# result_backend = 'redis://127.0.0.1:6379/0'
# result_backend = 'amqp://guest:guest@localhost//'
result_expires = 3600
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
task_always_eager = True
task_eager_propagates = True
enable_utc = False
max_retries = 0
retry_delay = 3

# 设置日志级别
worker_log_level = 'INFO'
beat_log_level = 'INFO'

# Celery Beat Settings - use the default scheduler
beat_scheduler = 'celery.beat.PersistentScheduler'

# Queue settings
task_default_queue = 'default'
task_create_missing_queues = True

task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
    Queue('low_priority', Exchange('low_priority'), routing_key='low_priority'),
)

task_routes = {
    'puti.celery_queue.simplified_tasks.generate_tweet_task': {'queue': 'high_priority'},
    'puti.celery_queue.simplified_tasks.check_dynamic_schedules': {'queue': 'default'},
}

# Schedule settings
beat_schedule = {
    # Check dynamic schedules every minute
    'check-dynamic-schedules': {
        'task': 'puti.celery_queue.simplified_tasks.check_dynamic_schedules',
        'schedule': crontab(minute='*'),  # Run every minute
        'args': (),
        'options': {'queue': 'default'}
    },
}

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000

# Other settings
task_time_limit = 600  # 10 minutes
task_soft_time_limit = 500  # 8.33 minutes

# Logging settings
worker_hijack_root_logger = False

broker_transport_options = {
    'visibility_timeout': 600,
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2
}
