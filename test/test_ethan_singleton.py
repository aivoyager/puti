"""
@Author: obstacle 
@Time: 30/08/24
@Description: 测试Ethan实例的单例模式和线程安全性
"""
import unittest
import threading
import time
import os
from unittest.mock import patch

from puti.celery_queue.simplified_tasks import get_ethan_instance


class TestEthanSingleton(unittest.TestCase):
    """测试Ethan实例的单例模式和线程安全性"""
    
    def setUp(self):
        """设置测试环境"""
        # 确保环境变量设置正确
        if 'PUTI_DATA_PATH' not in os.environ:
            os.environ['PUTI_DATA_PATH'] = '/tmp/puti_test'
            
    def test_singleton_pattern(self):
        """测试Ethan实例是单例模式"""
        # 获取两次实例
        instance1 = get_ethan_instance()
        instance2 = get_ethan_instance()
        
        # 确保两个实例是同一个对象
        self.assertIs(instance1, instance2)
        
    def test_thread_safety(self):
        """测试多线程环境下Ethan实例的线程安全性"""
        # 存储不同线程获取的实例
        instances = []
        errors = []
        
        # 用于创建实例的线程函数
        def create_instance():
            try:
                instance = get_ethan_instance()
                instances.append(instance)
            except Exception as e:
                errors.append(str(e))
        
        # 创建多个线程同时获取实例
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            
        # 启动所有线程
        for thread in threads:
            thread.start()
            
        # 等待所有线程完成
        for thread in threads:
            thread.join()
            
        # 确保没有错误发生
        self.assertEqual(len(errors), 0, f"错误发生: {errors}")
        
        # 确保获取的所有实例都是同一个实例
        for i in range(1, len(instances)):
            self.assertIs(instances[0], instances[i])
            
    def test_error_recovery(self):
        """测试错误恢复功能"""
        # 获取初始实例
        instance1 = get_ethan_instance()
        
        # 模拟实例损坏
        # 通过直接修改模块中的_ethan_instance变量（这只是为了测试）
        import puti.celery_queue.simplified_tasks
        puti.celery_queue.simplified_tasks._ethan_instance = None
        
        # 重新获取实例
        instance2 = get_ethan_instance()
        
        # 确保新实例是有效的
        self.assertIsNotNone(instance2)
        self.assertEqual(instance2.__class__.__name__, "EthanG")

    @patch('puti.llm.graph.ethan_graph.Graph')
    @patch('puti.llm.graph.ethan_graph.Vertex')
    def test_singleton_behavior(self, mock_vertex, mock_graph):
        import puti.celery_queue.simplified_tasks
        puti.celery_queue.simplified_tasks._ethan_instance = None
        # First call to get_ethan_instance should create a new instance
        ethan1 = get_ethan_instance()
        self.assertIsNotNone(ethan1)


if __name__ == "__main__":
    unittest.main() 