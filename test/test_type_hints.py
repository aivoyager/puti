"""
@Author: obstacle 
@Time: 27/08/24
@Description: 测试类型提示是否正确工作
"""
import os
import tempfile


def test_type_hints():
    """测试 ScheduleManager 的类型提示"""
    # 创建临时目录和环境变量
    temp_dir = tempfile.mkdtemp()
    os.environ['PUTI_DATA_PATH'] = temp_dir
    
    try:
        # 导入相关模块
        from puti.db.schedule_manager import ScheduleManager
        from puti.db.model.task.bot_task import TweetSchedule
        
        # 创建 ScheduleManager 实例
        manager = ScheduleManager()
        
        # 创建一个调度任务
        schedule = manager.create_schedule(
            name="test_schedule",
            cron_schedule="* * * * *"
        )
        
        # 测试：获取调度任务并访问其字段
        retrieved = manager.get_by_id(schedule.id)
        
        # 访问 TweetSchedule 特有的字段
        # 这里的代码应该能够在IDE中获得字段提示
        print("Schedule name:", retrieved.name)
        print("Cron expression:", retrieved.cron_schedule)
        print("Is running:", retrieved.is_running)
        print("Last run:", retrieved.last_run)
        print("Next run:", retrieved.next_run)
        print("PID:", retrieved.pid)
        
        # 测试返回列表中的元素类型
        schedules = manager.get_all()
        if schedules:
            # 访问列表中第一个元素的字段
            # 这里的代码应该能够在IDE中获得字段提示
            first = schedules[0]
            print("First schedule name:", first.name)
            print("First schedule is running:", first.is_running)
            
        print("Type hints test completed successfully!")
        
    finally:
        # 清理
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_type_hints() 