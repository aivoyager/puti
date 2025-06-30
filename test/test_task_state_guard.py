"""
@Author: obstacle 
@Time: 30/08/24
@Description: 测试TaskStateGuard的状态同步功能
"""
import os
import unittest
import tempfile
from datetime import datetime, timedelta
import time

from puti.db.task_state_guard import TaskStateGuard
from puti.db.schedule_manager import ScheduleManager
from puti.constant.base import TaskType


class TestTaskStateGuard(unittest.TestCase):
    """测试TaskStateGuard类"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建临时目录和数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.temp_dir = tempfile.mkdtemp()
        
        # 设置环境变量
        os.environ['DB_PATH'] = self.temp_db.name
        os.environ['PUTI_DATA_PATH'] = self.temp_dir
        
        # 创建调度器管理器
        self.manager = ScheduleManager()
        self.manager.create_table()
        
    def tearDown(self):
        """清理测试环境"""
        # 移除临时文件和目录
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_normal_execution(self):
        """测试正常执行流程下的状态同步"""
        # 创建一个调度任务
        schedule = self.manager.create_schedule(
            name="test_normal",
            cron_schedule="*/5 * * * *",
            enabled=True
        )
        
        # 模拟分配任务ID
        self.manager.update(schedule.id, {"task_id": "test-task-123"})
        
        # 使用TaskStateGuard执行任务
        with TaskStateGuard(task_id="test-task-123") as guard:
            # 模拟执行任务
            time.sleep(0.1)
            # 使用已存在的字段而不是progress
            guard.update_state(task_id="updated-task-123")
        
        # 检查任务状态
        updated = self.manager.get_by_id(schedule.id)
        self.assertFalse(updated.is_running)
        self.assertIsNone(updated.pid)
        self.assertIsNotNone(updated.last_run)
        self.assertEqual(updated.task_id, "updated-task-123")
    
    def test_exception_handling(self):
        """测试异常情况下的状态同步"""
        # 创建一个调度任务
        schedule = self.manager.create_schedule(
            name="test_exception",
            cron_schedule="*/5 * * * *",
            enabled=True
        )
        
        # 更新任务ID
        self.manager.update(schedule.id, {"task_id": "test-task-456"})
        
        try:
            # 使用TaskStateGuard执行任务，但会抛出异常
            with TaskStateGuard(task_id="test-task-456") as guard:
                # 模拟执行任务
                time.sleep(0.1)
                # 抛出异常
                raise ValueError("Test exception")
        except ValueError:
            pass  # 我们期望异常被抛出
            
        # 检查任务状态 - 应该被正确重置
        updated = self.manager.get_by_id(schedule.id)
        self.assertFalse(updated.is_running)
        self.assertIsNone(updated.pid)
        # last_run在异常情况下不应该更新
        self.assertIsNone(updated.last_run)
    
    def test_for_task_context_manager(self):
        """测试for_task类方法"""
        # 创建一个调度任务
        schedule = self.manager.create_schedule(
            name="test_for_task",
            cron_schedule="*/5 * * * *",
            enabled=True
        )
        
        # 使用for_task类方法
        with TaskStateGuard.for_task(schedule_id=schedule.id) as guard:
            # 模拟执行任务
            time.sleep(0.1)
            # 不使用status字段，因为它不存在于TweetSchedule模型中
            # 而是使用已有字段
            guard.update_state(task_id="custom-task-id")
        
        # 检查任务状态
        updated = self.manager.get_by_id(schedule.id)
        self.assertFalse(updated.is_running)
        self.assertEqual(updated.task_id, "custom-task-id")
        self.assertIsNotNone(updated.last_run)
    
    def test_next_run_calculation(self):
        """测试任务完成后next_run的计算"""
        # 创建一个调度任务
        schedule = self.manager.create_schedule(
            name="test_next_run",
            cron_schedule="*/5 * * * *",  # 每5分钟运行
            enabled=True
        )
        
        # 手动设置一个明显不同的next_run以方便测试
        old_next_run = datetime.now() - timedelta(days=1)  # 设置为一天前
        self.manager.update(schedule.id, {"next_run": old_next_run})
        
        # 重新加载调度任务
        schedule = self.manager.get_by_id(schedule.id)
        initial_next_run = schedule.next_run
        
        # 使用TaskStateGuard执行任务
        with TaskStateGuard(schedule_id=schedule.id) as guard:
            # 模拟执行任务
            time.sleep(0.1)
        
        # 检查next_run是否被更新
        updated = self.manager.get_by_id(schedule.id)
        self.assertIsNotNone(updated.next_run)
        self.assertNotEqual(str(updated.next_run), str(initial_next_run), 
                           f"Next run time didn't change: {updated.next_run} vs {initial_next_run}")
        
        # 确认next_run是在当前时间之后
        self.assertGreater(updated.next_run, datetime.now())


if __name__ == "__main__":
    unittest.main() 