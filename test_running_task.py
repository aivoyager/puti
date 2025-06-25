#!/usr/bin/env python

import os
import sys
import sqlite3
from pathlib import Path

# 使用环境变量获取数据路径
if 'PUTI_DATA_PATH' in os.environ:
    data_path = os.environ['PUTI_DATA_PATH']
else:
    # 设置默认的数据路径
    data_path = str(Path.home() / 'puti' / 'data')
    if not Path(data_path).exists():
        data_path = str(Path.home() / 'puti')
    os.environ['PUTI_DATA_PATH'] = data_path

print(f"Using data path: {data_path}")

# 寻找所有可能的SQLite数据库文件
sqlite_paths = []
for path in [data_path, Path(data_path).parent]:
    sqlite_file = Path(path) / 'puti.sqlite'
    if sqlite_file.exists():
        sqlite_paths.append(sqlite_file)

if not sqlite_paths:
    print("未找到SQLite数据库文件!")
    sys.exit(1)

# 对每个数据库文件执行操作
for db_path in sqlite_paths:
    print(f"\n尝试使用数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询所有任务
    cursor.execute("SELECT id, name, is_running, task_id, enabled FROM tweet_schedules WHERE is_del = 0")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  在 {db_path} 中没有找到任何任务")
        conn.close()
        continue
        
    print(f"  找到 {len(rows)} 个任务:")
    for row in rows:
        print(f"  任务ID: {row[0]}, 名称: {row[1]}, 状态: {'启用' if row[4] else '禁用'}, 运行状态: {'运行中' if row[2] else '未运行'}")

    # 选择任务ID为193的任务，如果存在的话
    cursor.execute("SELECT id, name FROM tweet_schedules WHERE id = 193 AND is_del = 0")
    target_task = cursor.fetchone()
    
    if target_task:
        task_id = target_task[0]
        task_name = target_task[1]
    else:
        # 如果193不存在，选择第一个任务
        task_id = rows[0][0]
        task_name = rows[0][1]
    
    celery_task_id = "test-task-id-123456"  # 模拟的Celery任务ID
    
    print(f"\n  将任务 {task_id} ({task_name}) 标记为运行中...")
    cursor.execute("UPDATE tweet_schedules SET is_running = 1, task_id = ? WHERE id = ?", 
                   (celery_task_id, task_id))
    conn.commit()
    
    # 验证更新
    cursor.execute("SELECT id, name, is_running, task_id FROM tweet_schedules WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row:
        print(f"  更新后状态:")
        print(f"  任务ID: {row[0]}")
        print(f"  名称: {row[1]}")
        print(f"  运行状态: {'运行中' if row[2] else '未运行'}")
        print(f"  Celery任务ID: {row[3]}")
    
    conn.close()

print("\n测试完成") 