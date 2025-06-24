"""
@Author: obstacle
@Time: 20/01/25 15:14
@Description:  
"""
from celery import Celery
from puti.conf import celery_config
# Import the simplified tasks directly instead of using autodiscover
from celery_queue.simplified_tasks import check_dynamic_schedules, generate_tweet_task


def make_celery(app_name):
    cel_app = Celery(app_name)
    cel_app.conf.update(result_expires=3600)
    cel_app.config_from_object(celery_config)
    
    # Register our tasks manually instead of using autodiscover
    # This avoids loading problematic modules
    cel_app.tasks.register(check_dynamic_schedules)
    cel_app.tasks.register(generate_tweet_task)
    
    return cel_app


app = make_celery('tasks')
celery_app = app  # For backwards compatibility
