"""
@Author: obstacle
@Time: 20/01/25 15:14
@Description:  
"""
from celery import Celery
from conf import celery_config
# from . import tasks


def make_celery(app_name):
    cel_app = Celery(app_name)
    cel_app.conf.update(result_expires=3600)
    cel_app.config_from_object(celery_config)
    # 确保自动发现包含所有任务模块
    cel_app.autodiscover_tasks(packages=['celery_queue'], related_name='tasks')
    return cel_app


celery_app = make_celery('tasks')
