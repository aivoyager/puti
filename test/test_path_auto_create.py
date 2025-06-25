"""
@Author: obstacles
@Time: 26/06/25 16:30
@Description: 测试Pathh类的自动路径创建功能
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# 先导入并修改配置
with patch('pathlib.Path.home') as mock_home:
    # 创建临时目录
    temp_dir = tempfile.TemporaryDirectory()
    mock_home.return_value = Path(temp_dir.name)
    
    # 确保导入时会使用临时目录
    from puti.constant.base import PathAutoCreate, Pathh, Base


class TestPathAutoCreate(unittest.TestCase):
    """测试PathAutoCreate类"""
    
    def setUp(self):
        # 创建临时目录用于测试
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        # 清理临时目录
        self.temp_dir.cleanup()
    
    def test_ensure_path_for_file(self):
        """测试确保文件路径的父目录存在"""
        # 创建一个不存在的多级目录下的文件路径
        test_file_path = str(self.temp_path / "dir1" / "dir2" / "test.txt")
        
        # 确认父目录不存在
        parent_dir = Path(test_file_path).parent
        self.assertFalse(parent_dir.exists())
        
        # 调用确保路径存在的方法
        result = PathAutoCreate.ensure_path(test_file_path)
        
        # 验证返回值是原始路径
        self.assertEqual(result, test_file_path)
        
        # 验证父目录已被创建
        self.assertTrue(parent_dir.exists())
        
        # 验证文件本身没有被创建
        self.assertFalse(Path(test_file_path).exists())
    
    def test_ensure_path_for_directory(self):
        """测试确保目录路径存在"""
        # 创建一个不存在的多级目录路径
        test_dir_path = str(self.temp_path / "dir1" / "dir2" / "dir3")
        
        # 确认目录不存在
        self.assertFalse(Path(test_dir_path).exists())
        
        # 调用确保路径存在的方法
        result = PathAutoCreate.ensure_path(test_dir_path)
        
        # 验证返回值是原始路径
        self.assertEqual(result, test_dir_path)
        
        # 验证目录已被创建
        self.assertTrue(Path(test_dir_path).exists())


class TestPathEnum(unittest.TestCase):
    """测试Pathh枚举类的直接使用方法"""
    
    def test_direct_pathh_val_creates_directory(self):
        """直接测试Pathh.CONFIG_DIR.val是否会自动创建目录"""
        # 直接使用Pathh.CONFIG_DIR.val
        config_dir_path = Path(Pathh.CONFIG_DIR.val)
        
        # 验证目录已被创建
        self.assertTrue(config_dir_path.exists())
        
        # 清理，为其他测试准备
        if config_dir_path.exists():
            # 可能会有子目录或文件，所以这里不直接删除
            pass
    
    def test_direct_pathh_call_creates_directory(self):
        """直接测试调用Pathh.CONFIG_DIR()是否会自动创建目录"""
        # 直接使用Pathh.CONFIG_DIR()
        config_dir_path = Path(Pathh.CONFIG_DIR())
        
        # 验证目录已被创建
        self.assertTrue(config_dir_path.exists())
    
    def test_direct_pathh_file_parent_directory_created(self):
        """直接测试访问文件路径是否会自动创建其父目录"""
        # 直接使用Pathh.CONFIG_FILE.val
        config_file_path = Path(Pathh.CONFIG_FILE.val)
        config_dir_path = config_file_path.parent
        
        # 验证父目录已被创建（这是我们真正关心的）
        self.assertTrue(config_dir_path.exists())
        
        # 不再验证文件是否存在，因为可能已经被其他测试创建
        # 或者系统中已经存在此文件


if __name__ == "__main__":
    unittest.main() 