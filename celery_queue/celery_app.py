"""
@Author: obstacle
@Time: 20/01/25 15:14
@Description:  
"""
from celery import Celery
from conf import celery_config

def make_celery(app_name):
    cel_app = Celery(app_name)
    cel_app.conf.update(result_expires=3600)
    cel_app.config_from_object(celery_config)
    return cel_app


celery_app = make_celery('tasks')
