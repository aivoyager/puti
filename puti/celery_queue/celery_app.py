"""
@Author: obstacle
@Time: 20/01/25 15:14
@Description:  
"""
import os
from pathlib import Path
from celery import Celery
from puti.conf import celery_config
from puti.constant.base import Pathh


def make_celery(app_name):
    cel_app = Celery(app_name)
    cel_app.conf.update(result_expires=3600)

    beat_db_path = Pathh.BEAT_DB.val

    cel_app.conf.update(
        beat_schedule_filename=str(beat_db_path)
    )

    cel_app.config_from_object(celery_config)

    cel_app.autodiscover_tasks(['puti.celery_queue', 'puti.celery_queue.simplified_tasks'])

    return cel_app


app = make_celery('tasks')
celery_app = app  # For backwards compatibility
