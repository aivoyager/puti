#!/usr/bin/env python3
"""
简化版CLI入口点，只包含scheduler功能
"""
import os
import sys
import click
from pathlib import Path

# 设置环境变量
if not os.environ.get('PUTI_DATA_PATH'):
    data_path = os.path.expanduser('~/puti/data')
    os.makedirs(data_path, exist_ok=True)
    os.environ['PUTI_DATA_PATH'] = data_path
    print(f"Set PUTI_DATA_PATH to {data_path}")

# 创建一个自定义的上下文设置
class PutiCLI(click.Group):
    def make_context(self, info_name, args, parent=None, **extra):
        # 使用'puti'作为命令名
        return super().make_context('puti', args, parent=parent, **extra)

@click.group(cls=PutiCLI)
def cli():
    """Puti CLI工具: 用于管理Tweet调度器的命令行工具。"""
    pass

@cli.group()
def scheduler():
    """
    管理tweet调度器操作。
    
    此命令组提供以下工具：
    
    1. 启动/停止调度器守护进程
    2. 创建和配置tweet调度计划
    3. 查看任务状态和调度信息
    4. 监控日志和工作进程活动
    """
    pass

@scheduler.command()
def start():
    """启动调度器守护进程。"""
    os.system("./puti-cmd start")

@scheduler.command()
def stop():
    """停止调度器守护进程。"""
    os.system("./puti-cmd stop")

@scheduler.command()
def status():
    """检查调度器守护进程的状态。"""
    os.system("./puti-cmd status")

@scheduler.command()
@click.option('--all', '-a', is_flag=True, help="显示所有计划，包括已禁用的")
@click.option('--running', '-r', is_flag=True, help="只显示当前正在运行的计划")
def list(all, running):
    """列出所有计划任务。"""
    cmd = "./puti-cmd list"
    if all:
        cmd += " --all"
    if running:
        cmd += " --running"
    os.system(cmd)

@scheduler.command()
@click.argument('name', required=True)
@click.argument('cron', required=True)
@click.option('--topic', '-t', help='推文生成的主题')
@click.option('--disabled', is_flag=True, help='创建时禁用此计划')
def create(name, cron, topic=None, disabled=False):
    """创建新的计划推文任务。"""
    cmd = f'./puti-cmd create {name} "{cron}"'
    if topic:
        cmd += f' --topic "{topic}"'
    if disabled:
        cmd += ' --disabled'
    os.system(cmd)

@scheduler.command()
@click.argument('schedule_id', type=int)
def enable(schedule_id):
    """启用特定计划。"""
    os.system(f"./puti-cmd enable {schedule_id}")

@scheduler.command()
@click.argument('schedule_id', type=int)
def disable(schedule_id):
    """禁用特定计划。"""
    os.system(f"./puti-cmd disable {schedule_id}")

@scheduler.command()
@click.argument('schedule_id', type=int)
def delete(schedule_id):
    """删除特定计划。"""
    os.system(f"./puti-cmd delete {schedule_id}")

@scheduler.command()
@click.argument('schedule_id', type=int)
def run(schedule_id):
    """手动运行特定计划任务。"""
    os.system(f"./puti-cmd run {schedule_id}")

if __name__ == '__main__':
    cli() 