"""
@Author: obstacle
@Time: 20/01/25 15:45
@Description:  
"""

# broker_url = 'redis://127.0.0.1:6379/0'
broker_url = 'amqp://guest:guest@localhost//'
result_backend = 'redis://127.0.0.1:6379/0'
# result_backend = 'amqp://guest:guest@localhost//'
result_expires = 3600
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
enable_utc = False
beat_schedule = {
    'my-periodic-task': {
        'task': 'puti.celery_queue.tasks.add',
        'schedule': 1.0,
        # 'schedule': crontab(minute='*/1'),  # 每分钟执行一次 ----
        # 'schedule': schedule(run_every=1),
        'args': (1, 2)  # 任务参数
    }
}
