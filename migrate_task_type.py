#!/usr/bin/env python
"""
迁移脚本：为tweet_schedules表添加task_type列
"""
import sqlite3
import os
from pathlib import Path

def migrate_task_type():
    """向tweet_schedules表添加task_type列"""
    # 获取数据库路径
    db_path = Path.home() / 'puti' / 'data' / 'puti.sqlite'
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False
    
    print(f"正在连接数据库: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tweet_schedules'")
        if not cursor.fetchone():
            print("tweet_schedules表不存在，无需迁移")
            return False
        
        # 检查task_type列是否已存在
        cursor.execute("PRAGMA table_info(tweet_schedules)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"当前表列: {columns}")
        
        if 'task_type' in columns:
            print("task_type列已存在，无需迁移")
            return True
        
        # 开始事务
        conn.execute("BEGIN TRANSACTION")
        
        # 添加task_type列，默认值为'post'
        print("正在添加task_type列...")
        cursor.execute("ALTER TABLE tweet_schedules ADD COLUMN task_type TEXT DEFAULT 'post'")
        
        # 提交事务
        conn.commit()
        print("迁移成功完成！")
        return True
    
    except Exception as e:
        # 发生异常时回滚
        conn.rollback()
        print(f"迁移失败: {str(e)}")
        return False
    
    finally:
        # 关闭连接
        conn.close()

if __name__ == "__main__":
    print("开始迁移数据库...")
    if migrate_task_type():
        print("数据库迁移成功")
    else:
        print("数据库迁移失败") 