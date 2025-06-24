#!/usr/bin/env python
from puti import bootstrap
from puti.db.schedule_manager import ScheduleManager
from puti.constant.base import TaskType

# 初始化管理器
mgr = ScheduleManager()

# 获取所有记录
all_schedules = mgr.get_all()
print(f'总计记录: {len(all_schedules)}')

# 获取未删除记录
active_schedules = mgr.get_all(where_clause='is_del = 0')
print(f'未删除记录: {len(active_schedules)}')

# 获取已删除记录
deleted_schedules = mgr.get_all(where_clause='is_del = 1')
print(f'已删除记录: {len(deleted_schedules)}')

# 显示已删除记录详情
if deleted_schedules:
    print('\n已删除记录详情:')
    for s in deleted_schedules:
        task_type_display = next((t.dsp for t in TaskType if t.val == s.task_type), s.task_type)
        print(f'ID: {s.id}, 名称: {s.name}, 类型: {s.task_type} ({task_type_display}), 是否删除: {s.is_del}')

# 显示未删除记录详情
if active_schedules:
    print('\n未删除记录详情:')
    for s in active_schedules:
        task_type_display = next((t.dsp for t in TaskType if t.val == s.task_type), s.task_type)
        print(f'ID: {s.id}, 名称: {s.name}, 类型: {s.task_type} ({task_type_display}), 是否删除: {s.is_del}') 