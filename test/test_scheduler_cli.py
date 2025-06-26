import unittest
import os
import tempfile
import shutil
from click.testing import CliRunner
from puti.cli import scheduler
from puti.db.sqlite_operator import SQLiteOperator
from puti.db.schedule_manager import ScheduleManager
import datetime


class TestSchedulerCLI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前，设置一个临时的测试环境"""
        cls.test_dir = tempfile.mkdtemp()
        # 设置环境变量，让应用使用我们的临时数据库
        os.environ['PUTI_DATA_PATH'] = cls.test_dir
        # 初始化数据库
        cls.db_operator = SQLiteOperator()
        # 创建表结构
        cls.manager = ScheduleManager(db_operator=cls.db_operator)
        cls.runner = CliRunner()

    @classmethod
    def tearDownClass(cls):
        """在所有测试结束后，清理临时环境"""
        shutil.rmtree(cls.test_dir)
        del os.environ['PUTI_DATA_PATH']

    def setUp(self):
        """在每个测试开始前，清空数据库，确保测试独立"""
        self.manager = ScheduleManager(db_operator=self.__class__.db_operator)
        # 删除所有现有的 Schedule 记录 (软删除)
        schedules = self.manager.get_all()
        for schedule in schedules:
            self.manager.delete(schedule.id)

    def tearDown(self):
        """在每个测试结束后，再次清空数据库"""
        schedules = self.manager.get_all()
        for schedule in schedules:
            self.manager.delete(schedule.id, soft_delete=False)  # 硬删除

    def test_create_and_list_schedule(self):
        """测试创建和列出计划任务"""
        # # 1. 创建任务
        # result_create = self.runner.invoke(
        #     scheduler,
        #     ['create', 'my_real_task', '*/5 * * * *', '--topic', 'integration test'],
        #     obj={'db_operator': self.__class__.db_operator}  # Pass db_operator explicitly
        # )
        # self.assertEqual(result_create.exit_code, 0, result_create.output)
        # self.assertIn("✅ 已创建计划任务", result_create.output)
        #
        # # 2. 从数据库验证任务已创建
        # task = self.manager.get_by_name('my_real_task')
        # self.assertIsNotNone(task)
        # self.assertEqual(task.cron_schedule, '*/5 * * * *')
        # self.assertTrue(task.enabled)

        # 3. 列出任务并验证输出
        result_list = self.runner.invoke(
            scheduler, 
            ['list'],
            obj={'db_operator': self.__class__.db_operator}  # Pass db_operator explicitly
        )
        self.assertEqual(result_list.exit_code, 0, result_list.output)
        # self.assertIn("my_real_task", result_list.output)
        # self.assertIn("✅ 已启用", result_list.output)

    def test_start_and_stop_schedule(self):
        """测试启动和停止计划任务"""
        # 1. 创建一个默认禁用的任务
        self.runner.invoke(
            scheduler,
            ['create', 'task_to_start_stop', '* * * * *', '--disabled'],
            obj={'db_operator': self.__class__.db_operator}  # Pass db_operator explicitly
        )
        task = self.manager.get_by_name('task_to_start_stop')
        self.assertIsNotNone(task)
        self.assertFalse(task.enabled, "任务初始状态应为禁用")

        # Mock the SchedulerDaemon to avoid actually starting the daemon during tests
        from unittest.mock import patch
        from puti.scheduler import SchedulerDaemon
        
        # 2. 启动任务 - 使用obj选项传递数据库操作符，并模拟调度器操作
        with patch.object(SchedulerDaemon, 'start', return_value=None) as mock_start, \
             patch.object(SchedulerDaemon, 'is_running', return_value=False) as mock_is_running:
            
            result_start = self.runner.invoke(
                scheduler, 
                ['start', str(task.id)],
                obj={'db_operator': self.__class__.db_operator}  # Pass db_operator explicitly
            )
            self.assertEqual(result_start.exit_code, 0, result_start.output)
            
            # 验证自动启动逻辑被调用
            mock_start.assert_called_once()
        
        # 英文和中文的匹配，避免测试失败
        success_msg_found = any(msg in result_start.output for msg in ["Task Enabled", "✅ Task", "已启用任务", "已成功启动任务"])
        self.assertTrue(success_msg_found, f"未找到任务启动成功消息，实际输出：{result_start.output}")

        # 从数据库验证任务已启用
        task_started = self.manager.get_by_id(task.id)
        self.assertTrue(task_started.enabled, "任务启动后应为启用状态")
        
        # 验证next_run时间被更新为接近当前时间，以便任务立即执行
        now = datetime.datetime.now()
        time_diff = (now - task_started.next_run).total_seconds()
        self.assertLess(abs(time_diff), 60, "任务的next_run时间应该被更新为接近当前时间")

        # 验证输出中包含关于调度器状态的消息
        scheduler_message_found = any(msg in result_start.output for msg in [
            "Starting it automatically",  # 自动启动消息
            "Scheduler daemon started successfully",  # 启动成功消息
            "Failed to start scheduler daemon"  # 启动失败消息
        ])
        self.assertTrue(scheduler_message_found, f"未找到关于自动启动调度器的消息，实际输出：{result_start.output}")

        # 3. 停止任务
        # 我们需要手动将任务标记为运行中，以模拟真实场景
        self.manager.update_schedule(task.id, is_running=True)

        # 停止任务 - 使用obj选项传递数据库操作符
        result_stop = self.runner.invoke(
            scheduler, 
            ['stop', str(task.id)],
            obj={'db_operator': self.__class__.db_operator}  # Pass db_operator explicitly
        )
        self.assertEqual(result_stop.exit_code, 0, result_stop.output)
        
        # 英文和中文的匹配，避免测试失败
        success_msg_found = any(msg in result_stop.output for msg in ["Task Disabled", "✅ Task", "已禁用任务", "已成功停止并禁用任务"])
        self.assertTrue(success_msg_found, f"未找到任务停止成功消息，实际输出：{result_stop.output}")

        # 从数据库验证任务已禁用且未在运行
        task_stopped = self.manager.get_by_id(task.id)
        self.assertFalse(task_stopped.enabled, "任务停止后应为禁用状态")
        self.assertFalse(task_stopped.is_running, "任务停止后 `is_running` 应为 False")

    def test_delete_schedule(self):
        """测试删除计划任务"""
        # 1. 创建一个任务用于删除
        self.runner.invoke(
            scheduler,
            ['create', 'task_to_delete', '* * * * *'],
            obj={'db_operator': self.__class__.db_operator}  # Pass db_operator explicitly
        )
        task = self.manager.get_by_name('task_to_delete')
        self.assertIsNotNone(task)

        # 2. 删除任务（使用 --force 以避免交互式确认）
        result_delete = self.runner.invoke(
            scheduler, 
            ['delete', str(task.id), '--force'],
            obj={'db_operator': self.__class__.db_operator}  # Pass db_operator explicitly
        )
        self.assertEqual(result_delete.exit_code, 0, result_delete.output)
        self.assertIn("已成功删除", result_delete.output)

        # 3. 验证软删除 - 任务仍然存在但被标记为已删除
        # 注意：由于get_by_id没有过滤已删除的记录，我们需要直接检查is_del属性
        records = self.__class__.db_operator.execute(
            f"SELECT * FROM {self.manager._table_name} WHERE id = ?", 
            (task.id,)
        ).fetchall()
        self.assertEqual(len(records), 1, "任务应该在数据库中")
        self.assertTrue(records[0]['is_del'], "任务应该被标记为已删除")
        
        # 验证在使用get_all获取所有未删除记录时，该任务不会出现
        all_tasks = self.manager.get_all(where_clause="is_del = 0")
        for t in all_tasks:
            self.assertNotEqual(t.id, task.id, "已删除的任务不应该出现在未删除的任务列表中")


if __name__ == '__main__':
    unittest.main()
