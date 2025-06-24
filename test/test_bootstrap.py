#!/usr/bin/env python
"""
测试bootstrap.py中的开发环境设置功能
"""
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保puti可以被导入
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from puti.bootstrap import setup_dev_environment


class TestBootstrap(unittest.TestCase):
    """测试bootstrap模块的开发环境设置功能"""
    
    def setUp(self):
        """创建临时目录作为测试项目目录"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """测试结束后清理临时目录"""
        shutil.rmtree(self.temp_dir)
    
    @patch('subprocess.run')
    @patch('puti.bootstrap.os.environ', new_callable=dict)
    def test_setup_dev_environment(self, mock_environ, mock_run):
        """测试setup_dev_environment函数的基本功能"""
        # 设置mock
        mock_run.return_value = MagicMock(returncode=0)
        mock_environ['PATH'] = '/original/path'
        
        # 运行函数
        result = setup_dev_environment(self.temp_dir)
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证subprocess.run被调用
        self.assertTrue(mock_run.called)
        
        # 验证环境变量被设置
        self.assertIn('VIRTUAL_ENV', mock_environ)
        self.assertIn('/bin:', mock_environ['PATH']) # 检查PATH是否被更新
        
        # 检查调用参数
        calls = mock_run.call_args_list
        
        # 至少应该有两次调用：一次创建venv，一次pip install
        self.assertGreaterEqual(len(calls), 2)
        
        # 检查是否有调用pip install -e
        pip_install_calls = [call for call in calls if 'install' in str(call) and '-e' in str(call)]
        self.assertGreaterEqual(len(pip_install_calls), 1)
    
    @patch('subprocess.run')
    def test_setup_dev_environment_error_handling(self, mock_run):
        """测试setup_dev_environment函数的错误处理"""
        # 设置mock抛出异常
        mock_run.side_effect = Exception("Test error")
        
        # 运行函数
        result = setup_dev_environment(self.temp_dir)
        
        # 验证结果
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main() 