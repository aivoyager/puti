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
    
    # 设置Beat数据库文件存储位置
    config_dir = Path(Pathh.CONFIG_DIR.val)
    config_dir.mkdir(parents=True, exist_ok=True)
    beat_db_path = config_dir / 'celerybeat-schedule.db'
    
    # 更新配置
    cel_app.conf.update(
        beat_schedule_filename=str(beat_db_path)
    )
    
    cel_app.config_from_object(celery_config)
    
    # 不在这里直接导入任务，避免循环引用
    # 改为在任务文件中使用@shared_task装饰器
    
    return cel_app


app = make_celery('tasks')
celery_app = app  # For backwards compatibility
