#!/usr/bin/env python3
"""
简化版CLI入口点，只包含scheduler功能
这个脚本不依赖于twikit和其他非必要模块，可以直接运行。
"""
import os
import sys
import click
from pathlib import Path
import datetime

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
    from puti.scheduler import SchedulerDaemon
    
    daemon = SchedulerDaemon()
    daemon.start(activate_tasks=True)

@scheduler.command()
def stop():
    """停止调度器守护进程。"""
    from puti.scheduler import SchedulerDaemon
    
    daemon = SchedulerDaemon()
    daemon.stop()

@scheduler.command()
def status():
    """检查调度器守护进程的状态。"""
    from puti.scheduler import SchedulerDaemon
    from rich.console import Console
    
    console = Console()
    daemon = SchedulerDaemon()
    
    if daemon.is_running():
        pid = daemon._get_pid()
        console.print(f"[green]Scheduler is running with PID {pid}[/green]")
    else:
        console.print("[yellow]Scheduler is not running[/yellow]")

@scheduler.command()
@click.option('--all', '-a', is_flag=True, help="显示所有计划，包括已禁用的")
@click.option('--running', '-r', is_flag=True, help="只显示当前正在运行的计划")
def list(all, running):
    """列出所有计划任务。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    manager = ScheduleManager()
    
    if running:
        schedules = manager.get_running_schedules()
        table_title = "Currently Running Tasks"
    elif all:
        schedules = manager.get_all()
        table_title = "All Tasks (Including Disabled)"
    else:
        schedules = manager.get_active_schedules()
        table_title = "All Scheduled Tasks"
    
    table = Table(title=table_title)
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Cron Schedule")
    table.add_column("Enabled")
    table.add_column("Running")
    
    for schedule in schedules:
        enabled_icon = "✅" if schedule.enabled else "❌"
        running_icon = "✅" if schedule.is_running else "❌"
        
        table.add_row(
            str(schedule.id),
            schedule.name,
            schedule.cron_schedule,
            enabled_icon,
            running_icon
        )
    
    console.print(table)

@scheduler.command()
@click.argument('name', required=True)
@click.argument('cron', required=True)
@click.option('--topic', '-t', help='推文生成的主题')
@click.option('--disabled', is_flag=True, help='创建时禁用此计划')
def create(name, cron, topic=None, disabled=False):
    """创建新的计划推文任务。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    import datetime
    from croniter import croniter
    
    console = Console()
    manager = ScheduleManager()
    
    # 检查名称是否已存在
    existing = manager.get_by_name(name)
    if existing:
        console.print(f"[red]Error:[/red] Schedule with name '{name}' already exists (ID: {existing.id}).")
        console.print("Use a different name or delete the existing schedule first.")
        return
    
    # 验证cron表达式
    try:
        now = datetime.datetime.now()
        next_run = croniter(cron, now).get_next(datetime.datetime)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid cron expression: {cron}")
        console.print(f"Details: {str(e)}")
        return
    
    # 准备参数
    params = {}
    if topic:
        params['topic'] = topic
    
    # 创建计划
    try:
        schedule = manager.create_schedule(
            name=name,
            cron_schedule=cron,
            enabled=not disabled,
            params=params
        )
        
        console.print(f"[green]Created schedule:[/green] '{name}' (ID: {schedule.id})")
        console.print(f"Cron schedule: {cron}")
        console.print(f"Next run: {schedule.next_run}")
        console.print(f"Enabled: {'No' if disabled else 'Yes'}")
        
        if topic:
            console.print(f"Topic: {topic}")
            
        # 如果启用，触发立即检查
        if not disabled:
            try:
                from celery_queue.simplified_tasks import check_dynamic_schedules
                check_dynamic_schedules.delay()
                console.print("[green]Triggered schedule registration[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not trigger schedule check: {str(e)}[/yellow]")
                console.print("Schedule will be picked up on next Beat cycle.")
    except Exception as e:
        console.print(f"[red]Error creating schedule:[/red] {str(e)}")

@scheduler.command()
@click.argument('schedule_id', type=int)
def enable(schedule_id):
    """启用特定计划。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    if schedule.enabled:
        console.print(f"[yellow]Schedule '{schedule.name}' is already enabled.[/yellow]")
        return
    
    # 启用计划
    result = manager.update_schedule(schedule_id, enabled=True)
    
    if result:
        console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) has been enabled.[/green]")
        
        # 如果启用，触发立即检查
        try:
            from celery_queue.simplified_tasks import check_dynamic_schedules
            check_dynamic_schedules.delay()
            console.print("[green]Triggered an immediate schedule check.[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not trigger schedule check: {str(e)}[/yellow]")
    else:
        console.print(f"[red]Failed to enable schedule '{schedule.name}' (ID: {schedule_id}).[/red]")

@scheduler.command()
@click.argument('schedule_id', type=int)
def disable(schedule_id):
    """禁用特定计划。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    if not schedule.enabled:
        console.print(f"[yellow]Schedule '{schedule.name}' is already disabled.[/yellow]")
        return
    
    # 禁用计划
    result = manager.update_schedule(schedule_id, enabled=False)
    
    if result:
        console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) has been disabled.[/green]")
        
        # 如果计划正在运行，停止它
        if schedule.is_running:
            manager.stop_task(schedule_id)
            console.print(f"[yellow]Stopped running task for schedule '{schedule.name}'.[/yellow]")
    else:
        console.print(f"[red]Failed to disable schedule '{schedule.name}' (ID: {schedule_id}).[/red]")

@scheduler.command()
@click.argument('schedule_id', type=int)
def delete(schedule_id):
    """删除特定计划。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    # 如果计划正在运行，停止它
    if schedule.is_running:
        manager.stop_task(schedule_id)
    
    # 删除计划（使用硬删除实际移除它）
    result = manager.delete(schedule_id, soft_delete=False)
    if result:
        console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) has been deleted.[/green]")
    else:
        console.print(f"[red]Failed to delete schedule '{schedule.name}'.[/red]")

@scheduler.command()
@click.argument('schedule_id', type=int)
def run(schedule_id):
    """手动运行特定计划任务。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    import datetime
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    # 获取计划参数
    params = schedule.params or {}
    topic = params.get('topic')
    
    # 使用简化任务
    try:
        from celery_queue.simplified_tasks import generate_tweet_task
        task = generate_tweet_task.delay(topic=topic)
        console.print(f"[green]Task started![/green] Task ID: {task.id}")
        
        # 更新计划记录
        manager.update_schedule(schedule_id, 
            is_running=True,
            last_run=datetime.datetime.now(),
            task_id=task.id
        )
    except Exception as e:
        console.print(f"[red]Error starting task:[/red] {str(e)}")

if __name__ == '__main__':
    cli() 