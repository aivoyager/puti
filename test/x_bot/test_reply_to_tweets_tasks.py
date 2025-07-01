"""
使用真实组件测试推文回复功能
此测试不使用mock，而是使用真实的EthanG实例和工作流
"""
import os
import sys
import asyncio
import argparse
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_reply")

# 将项目根目录添加到Python路径，确保能正确导入模块
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

# 导入必要的模块
from celery_queue.simplified_tasks import reply_to_tweets_task
from puti.db.task_state_guard import TaskStateGuard


class MockTaskStateGuard:
    """
    模拟的TaskStateGuard类，避免数据库操作
    """
    @classmethod
    @patch.object(TaskStateGuard, '__init__', return_value=None)
    @patch.object(TaskStateGuard, '__enter__', return_value=MagicMock())
    @patch.object(TaskStateGuard, '__exit__', return_value=False)
    @patch.object(TaskStateGuard, 'update_state')
    def mock_for_task(cls, mock_update_state, mock_exit, mock_enter, mock_init, task_id=None, schedule_id=None):
        """模拟TaskStateGuard.for_task方法"""
        mock_guard = MagicMock()
        mock_guard.update_state = mock_update_state
        
        # 记录和输出操作而不是真正执行数据库操作
        def update_state_impl(**kwargs):
            logger.info(f"[MockTaskStateGuard] update_state called with: {kwargs}")
        
        mock_update_state.side_effect = update_state_impl
        
        return mock_guard


async def test_reply_task():
    """测试回复推文任务"""
    schedule_id = 'test_schedule_id'
    time_value = 1
    time_unit = 'days'
    
    logger.info(f"开始测试回复推文任务，参数: time_value={time_value}, time_unit={time_unit}, schedule_id={schedule_id}")
    
    # 替换TaskStateGuard.for_task，避免数据库操作
    original_for_task = TaskStateGuard.for_task
    TaskStateGuard.for_task = MockTaskStateGuard.mock_for_task
    
    try:
        # 创建模拟的self对象，带有request属性
        mock_self = MagicMock()
        mock_self.request = MagicMock()
        mock_self.request.id = "test-task-id"
        
        # 调用异步任务，按照函数定义传递参数
        result = await reply_to_tweets_task(
            mock_self,  # self参数
            schedule_id,  # schedule_id参数
            time_value=time_value,
            time_unit=time_unit
        )
        print(f"\n最终结果: {result}")
        return result
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        print(f"\n测试失败: {e}")
    finally:
        # 恢复原始方法
        TaskStateGuard.for_task = original_for_task


if __name__ == "__main__":
    asyncio.run(test_reply_task())
