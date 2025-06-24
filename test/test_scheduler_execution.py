#!/usr/bin/env python
"""
测试调度任务的执行和处理
此测试模块专注于测试调度任务的执行逻辑
"""
import os
import sys
import time
import pytest
import datetime
from pathlib import Path
from unittest.mock import patch

# 确保puti可以被导入
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 引入需要测试的模块
from puti import bootstrap  # 初始化所有环境变量
from puti.db.schedule_manager import ScheduleManager
from puti.db.model.task.bot_task import TweetSchedule
from puti.constant.base import Pathh

# 导入celery任务
try:
    from celery_queue.simplified_tasks import generate_tweet_task, check_dynamic_schedules
except ImportError:
    pytest.skip("Celery模块无法导入，跳过相关测试", allow_module_level=True)


# 使用实际的配置目录
@pytest.fixture(scope="module")
def real_data_path():
    """使用真实的数据目录"""
    config_dir = Path(Pathh.CONFIG_DIR.val)
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture(scope="module")
def schedule_manager():
    """提供一个ScheduleManager实例"""
    return ScheduleManager()


@pytest.fixture
def cleanup_schedules(schedule_manager):
    """每个测试前清理所有调度，确保测试环境干净"""
    yield
    schedules = schedule_manager.get_all()
    for schedule in schedules:
        if schedule.name.startswith("test_"):  # 只清理测试用的调度
            schedule_manager.delete(schedule.id)


# 测试任务记录的更新
def test_task_status_tracking(real_data_path, schedule_manager, cleanup_schedules):
    """测试任务状态跟踪功能"""
    # 创建一个测试调度
    schedule = schedule_manager.create_schedule(
        name="test_execution",
        cron_schedule="0 12 * * *",  # 每天中午12点
        enabled=True,
        params={"topic": "人工智能发展趋势", "hashtags": ["AI", "technology"]},
        task_type="post"  # 设置任务类型
    )

    # 记录ID用于后续查询
    schedule_id = schedule.id

    # 模拟任务启动
    with patch('celery_queue.simplified_tasks.generate_tweet_task.delay', return_value=type('obj', (object,), {'id': 'fake_task_id'})):
        result = schedule_manager.start_task(schedule_id)
        assert result == True

    # 验证任务状态已更新
    updated = schedule_manager.get_by_id(schedule_id)
    assert updated.is_running == True
    assert updated.task_id == "fake_task_id"
    assert updated.last_run is not None
    assert updated.task_type == "post"  # 确认任务类型未改变

    # 模拟任务停止
    result = schedule_manager.stop_task(schedule_id)
    assert result == True

    # 验证任务状态已更新
    completed = schedule_manager.get_by_id(schedule_id)
    assert completed.is_running == False
    assert completed.pid is None
    assert completed.task_type == "post"  # 确认任务类型未改变


# 测试cron表达式解析
def test_cron_expression_parsing(real_data_path, schedule_manager, cleanup_schedules):
    """测试cron表达式解析和下一次运行时间计算"""
    from croniter import croniter
    import datetime

    now = datetime.datetime.now()

    # 测试不同的cron表达式和不同的任务类型
    test_cases = [
        # 每天中午12点 - 发推任务
        {"cron": "0 12 * * *", "name": "test_daily_noon", "params": {"topic": "每日科技新闻汇总"}, "task_type": "post"},
        # 每小时整点 - 回复任务
        {"cron": "0 * * * *", "name": "test_hourly", "params": {"topic": "实时热点追踪"}, "task_type": "reply"},
        # 每5分钟 - 点赞任务
        {"cron": "*/5 * * * *", "name": "test_five_min", "params": {"topic": "快讯更新"}, "task_type": "like"},
        # 每周一上午9点 - 分析任务
        {"cron": "0 9 * * 1", "name": "test_monday_morning", "params": {"topic": "周一工作计划"}, "task_type": "analytics"}
    ]

    for case in test_cases:
        # 手动计算下一次运行时间
        cron = case["cron"]
        expected_next = croniter(cron, now).get_next(datetime.datetime)

        # 创建调度
        schedule = schedule_manager.create_schedule(
            name=case["name"],
            cron_schedule=cron,
            enabled=True,
            params=case["params"],
            task_type=case["task_type"]
        )

        # 检查计算的下一次运行时间是否与预期一致
        # 由于时间精度问题，只检查年、月、日、时、分
        actual_next = schedule.next_run
        assert actual_next.year == expected_next.year
        assert actual_next.month == expected_next.month
        assert actual_next.day == expected_next.day
        assert actual_next.hour == expected_next.hour
        assert actual_next.minute == expected_next.minute
        
        # 检查任务类型是否正确设置
        assert schedule.task_type == case["task_type"]


# 测试多个调度的并发执行
def test_concurrent_schedules(real_data_path, schedule_manager, cleanup_schedules):
    """测试多个调度的并发执行能力"""
    # 创建三个调度，所有都应该"立即"运行
    now = datetime.datetime.now()
    past_time = now - datetime.timedelta(minutes=5)

    schedules = []
    topics = ["人工智能", "区块链技术", "元宇宙发展"]
    task_types = ["post", "reply", "like"]  # 使用不同的任务类型
    
    for i in range(3):
        schedule = schedule_manager.create_schedule(
            name=f"test_concurrent_{i}",
            cron_schedule="*/5 * * * *",  # 每5分钟
            enabled=True,
            params={"topic": topics[i], "hashtags": ["tech", "innovation"]},
            task_type=task_types[i]  # 设置不同的任务类型
        )
        # 手动设置next_run为过去的时间，使它们在检查时都"应该运行"
        schedule_manager.update_schedule(
            schedule.id,
            next_run=past_time
        )
        schedules.append(schedule.id)

    # 使用任务ID的计数来验证所有调度是否都被处理
    task_ids = []
    processed_topics = []

    def fake_execute(*args, **kwargs):
        """模拟执行任务的函数，记录被调用的参数"""
        task_ids.append(kwargs.get('topic'))
        processed_topics.append(kwargs.get('topic'))
        # 返回一个伪任务ID
        return type('obj', (object,), {'id': f"fake_task_{len(task_ids)}"})

    # 替换实际执行函数
    with patch('celery_queue.simplified_tasks.generate_tweet_task.delay', side_effect=fake_execute):
        # 手动触发检查
        for schedule_id in schedules:
            schedule_manager.start_task(schedule_id)

    # 验证所有三个调度都被处理
    assert len(task_ids) == 3
    for topic in topics:
        assert topic in processed_topics
        
    # 当前ScheduleManager实现中，task_type未传递给实际任务，因此不检查任务类型
    # 而是检查所有调度的类型是否正确保存在数据库中
    for i, schedule_id in enumerate(schedules):
        updated_schedule = schedule_manager.get_by_id(schedule_id)
        assert updated_schedule.task_type == task_types[i]

    # 清理，停止所有运行中的任务
    for schedule_id in schedules:
        schedule_manager.stop_task(schedule_id)


# 测试参数传递
def test_params_passing(real_data_path, schedule_manager, cleanup_schedules):
    """测试参数是否正确传递给任务执行函数"""
    # 创建一个带有特定参数的调度
    params = {
        "topic": "中国科技创新",
        "hashtags": ["innovation", "china", "technology"],
        "mention_users": ["@techexpert", "@innovator"]
    }
    
    schedule = schedule_manager.create_schedule(
        name="test_params",
        cron_schedule="0 12 * * *",
        enabled=True,
        params=params,
        task_type="content_curation"  # 使用内容策划任务类型
    )
    
    captured_params = {}
    
    def capture_params(*args, **kwargs):
        """捕获传递给任务的参数"""
        nonlocal captured_params
        captured_params = kwargs
        return type('obj', (object,), {'id': 'fake_task_id'})
    
    # 替换实际执行函数
    with patch('celery_queue.simplified_tasks.generate_tweet_task.delay', side_effect=capture_params):
        schedule_manager.start_task(schedule.id)
    
    # 验证参数是否正确传递
    assert "topic" in captured_params
    assert captured_params["topic"] == params["topic"]
    
    # 在当前实现中，task_type并未传递给task，所以我们验证数据库中的记录
    updated_schedule = schedule_manager.get_by_id(schedule.id)
    assert updated_schedule.task_type == "content_curation"
    
    # 清理
    schedule_manager.stop_task(schedule.id)


if __name__ == "__main__":
    # 可以直接运行这个文件进行测试
    pytest.main([__file__, "-v"])
