"""
@Author: obstacle
@Time: 10/05/25 16:51
@Description: CLI commands for the PuTi package
"""
import os
import json
import click
import asyncio
import questionary
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from puti.core.config_setup import ensure_twikit_config_is_present
from puti.db.schedule_manager import ScheduleManager
from puti.scheduler import ensure_worker_running, ensure_beat_running, WorkerDaemon, BeatDaemon
from puti.llm.roles.agents import Alex, Ethan
from puti.constant.base import Pathh

# 创建全局console实例
console = Console()


@click.group()
def main():
    """Puti CLI Tool: An interactive AI assistant."""
    pass


@main.command()
@click.option('--name', default='Alex', help='Name of the Alex agent.')
def alex_chat(name):
    """Starts an interactive chat with Alex agent."""
    console.print(Panel(
        Markdown("Alex is an all-purpose bot with multiple integrated tools to help you with a wide range of tasks."),
        title="🤖 Meet Alex",
        border_style="cyan"
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
*   Press `Ctrl+D` or `Ctrl+C` to exit immediately.
""")
    console.print(welcome_message)

    alex_agent = Alex(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await questionary.text("👤 You:", qmark="").ask_async()
                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                console.print(Panel(user_input, title="👤 You", border_style="blue"))

                # Show a thinking indicator
                with console.status(f"[bold cyan]{name} is thinking...", spinner="dots"):
                    response = await alex_agent.run(user_input)

                # Print the response in a styled panel
                response_panel = Panel(
                    Markdown(response.content),
                    title=f"🤖 {name}",
                    border_style="green",
                    title_align="left"
            )
                console.print(response_panel)

            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C and Ctrl+D
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print("\n[bold yellow]Chat session ended. Goodbye![/bold yellow]")


@main.command()
@click.option('--name', default='Ethan', help='Name of the Ethan agent.')
def ethan_chat(name):
    """Starts an interactive chat with Ethan agent."""
    ensure_twikit_config_is_present()
    console.print(Panel(
        Markdown("Ethan is a Twitter bot designed to help you manage your daily Twitter activities."),
        title="🤖 Meet Ethan",
        border_style="cyan"
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
*   Press `Ctrl+D` or `Ctrl+C` to exit immediately.
""")
    console.print(welcome_message)

    ethan_agent = Ethan(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await questionary.text("👤 You:", qmark="").ask_async()
                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                console.print(Panel(user_input, title="👤 You", border_style="blue"))

                with console.status(f"[bold cyan]{name} is thinking...", spinner="dots"):
                    response = await ethan_agent.run(user_input)

                response_panel = Panel(
                    Markdown(response),
                    title=f"🤖 {name}",
                    border_style="green",
                    title_align="left"
            )
                console.print(response_panel)

            except (KeyboardInterrupt, EOFError):
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print("\n[bold yellow]Chat session ended. Goodbye![/bold yellow]")


@main.group()
@click.pass_context
def scheduler(ctx):
    """Scheduler for managing automated tasks."""
    console.print(Panel(Markdown("Starting Celery worker if not running..."), border_style="yellow"))
    if ensure_worker_running():
        console.print("[green]✓ Celery worker is running.[/green]")
    else:
        console.print("[red]✗ Failed to start Celery worker. Please check logs.[/red]")
        ctx.abort()
    
    ctx.obj = {'manager': ScheduleManager(), 'console': console}


@scheduler.command('list')
@click.pass_context
def list_tasks(ctx):
    """Lists all non-deleted tasks."""
    console = ctx.obj.get('console', Console())
    manager = ScheduleManager()
    tasks = manager.get_all(where_clause="is_del = 0")

    table = Table(title="Scheduled Tasks", border_style="cyan")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Name", style="bold")
    table.add_column("Enabled", justify="center")
    table.add_column("Task Type")
    table.add_column("CRON")
    table.add_column("Params")

    for task in tasks:
        enabled_str = "[green]Yes[/green]" if task.enabled else "[red]No[/red]"
        table.add_row(
            str(task.id),
            task.name,
            enabled_str,
            task.task_type_display,
            task.cron_schedule,
            str(task.params)
        )
    
    console.print(table)
    

@scheduler.command('create')
@click.argument('name')
@click.argument('cron')
@click.option('--type', 'task_type', required=True, help="Type of the task (e.g., 'post_tweet').")
@click.option('--params', help="JSON string of parameters for the task.", default='{}')
@click.pass_context
def create_task(ctx, name, cron, task_type, params):
    """Creates a new task (disabled by default)."""
    console = ctx.obj.get('console', Console())
    manager = ctx.obj['manager']
    try:
        import json
        params_dict = json.loads(params)
        
        task = manager.create_schedule(
            name=name,
            cron_schedule=cron,
            task_type=task_type,
            params=params_dict,
            enabled=False  # Always created as disabled
        )
        console.print(f"[green]✓ Task '{name}' created successfully with ID: {task.id}[/green]")
    except json.JSONDecodeError:
        console.print("[red]Error: Invalid JSON string for --params.[/red]")
    except Exception as e:
        console.print(f"[red]Error creating task: {str(e)}[/red]")


@scheduler.command('delete')
@click.argument('task_id', type=int)
@click.pass_context
def delete_task(ctx, task_id):
    """Logically deletes a task by setting is_del=1."""
    console = ctx.obj.get('console', Console())
    manager = ctx.obj['manager']
    task = manager.get_by_id(task_id)
    if not task:
        console.print(f"[red]Error: Task with ID {task_id} not found.[/red]")
        return
        
    manager.update(task_id, {'is_del': 1, 'enabled': False})
    console.print(f"[green]✓ Task '{task.name}' (ID: {task_id}) has been deleted.[/green]")
    ensure_beat_running()  # Ensure beat is running to pick up the change


@scheduler.command('start')
@click.argument('task_id', type=int)
@click.pass_context
def start_task(ctx, task_id):
    """Enables a disabled task and ensures the scheduler (beat) is running."""
    console = ctx.obj.get('console', Console())
    manager = ctx.obj['manager']
    task = manager.get_by_id(task_id)

    if not task:
        console.print(f"[red]Error: Task with ID {task_id} not found.[/red]")
        return
    if task.enabled:
        console.print(f"[yellow]Task '{task.name}' (ID: {task_id}) is already enabled.[/yellow]")
        return
    
    manager.update(task_id, {'enabled': True})
    console.print(f"[green]✓ Task '{task.name}' (ID: {task_id}) has been enabled.[/green]")

    console.print(Panel(Markdown("Ensuring Celery beat is running..."), border_style="yellow"))
    if ensure_beat_running():
        console.print("[green]✓ Celery beat is running.[/green]")
    else:
        console.print("[red]✗ Failed to start Celery beat. Please check logs.[/red]")


@scheduler.command('stop')
@click.argument('task_id', type=int)
@click.pass_context
def stop_task(ctx, task_id):
    """Disables an enabled task."""
    console = ctx.obj.get('console', Console())
    manager = ctx.obj['manager']
    task = manager.get_by_id(task_id)

    if not task:
        console.print(f"[red]Error: Task with ID {task_id} not found.[/red]")
        return
    if not task.enabled:
        console.print(f"[yellow]Task '{task.name}' (ID: {task_id}) is already disabled.[/yellow]")
        return
    
    manager.update(task_id, {'enabled': False})
    console.print(f"[green]✓ Task '{task.name}' (ID: {task_id}) has been disabled.[/green]")
    ensure_beat_running()  # Ensure beat is running to pick up the change


@scheduler.command('logs')
@click.argument('service', type=click.Choice(['worker', 'beat', 'scheduler']))
@click.option('--lines', '-n', default=20, help="Number of log lines to show.")
@click.option('--follow', '-f', is_flag=True, help="Follow log output in real-time.")
@click.option('--filter', help="Filter logs by keyword.")
@click.option('--level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), 
              help="Filter logs by minimum level.")
@click.option('--simple', is_flag=True, help="Use simple output format without timestamps.")
@click.option('--raw', is_flag=True, help="Show raw log output without any formatting.")
@click.pass_context
def show_logs(ctx, service, lines, follow, filter, level, simple, raw):
    """Shows logs for scheduler, worker, or beat services."""
    import re
    
    console = ctx.obj.get('console', Console())
    
    # 根据选择的服务类型确定日志文件路径
    if service == 'worker':
        log_file = Pathh.WORKER_LOG.val
    elif service == 'beat':
        log_file = Pathh.BEAT_LOG.val
    elif service == 'scheduler':
        # scheduler 日志实际上是 scheduler_beat.log
        log_file = str(Path(Pathh.CONFIG_DIR.val) / 'logs' / 'scheduler_beat.log')
    
    if not os.path.exists(log_file):
        console.print(f"[red]Log file not found at: {log_file}[/red]")
        return
    
    # 定义日志级别的样式映射和优先级
    log_level_styles = {
        'DEBUG': 'dim blue',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'bold red',
        'CRITICAL': 'bold red on white'
    }
    
    log_level_priority = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3,
        'CRITICAL': 4
    }
    
    min_level_priority = log_level_priority.get(level, 0) if level else 0
    
    # 用于识别不同日志格式的正则表达式模式
    # 1. 标准格式: [2025-06-25 12:00:32,330: WARNING/MainProcess]
    log_pattern1 = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}): (\w+)/(.+)\](.+)')
    # 2. 通用格式: 2023-01-01 13:45:01,123 | DEBUG | message
    log_pattern2 = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| (\w+)\s+ \| (.+)')
    
    def should_display_log(line, log_level=None):
        """根据过滤条件决定是否显示日志行"""
        # 关键字过滤
        if filter and filter.lower() not in line.lower():
            return False
            
        # 日志级别过滤
        if level and log_level:
            log_priority = log_level_priority.get(log_level, 0)
            if log_priority < min_level_priority:
                return False
                
        return True
    
    def format_log_line(line):
        """格式化日志行，添加颜色和样式"""
        line = line.strip()
        
        # 如果使用原始输出，只进行过滤，不进行格式化
        if raw:
            return None if not should_display_log(line) else line
        
        # 尝试匹配标准格式 [时间戳: 级别/进程]
        match = log_pattern1.match(line)
        if match:
            timestamp, log_level, process, content = match.groups()
            
            # 根据过滤条件决定是否显示
            if not should_display_log(line, log_level):
                return None
            
            # 简化格式，不显示时间戳
            if simple:
                level_style = log_level_styles.get(log_level, '')
                if level_style:
                    return f"[{level_style}]{log_level:8}[/{level_style}] ({process}) | {content.strip()}"
                else:
                    return f"{log_level:8} ({process}) | {content.strip()}"
            else:
                level_style = log_level_styles.get(log_level, '')
                if level_style:
                    return f"[dim]{timestamp}[/dim] | [{level_style}]{log_level:8}[/{level_style}] ({process}) | {content.strip()}"
                else:
                    return f"[dim]{timestamp}[/dim] | {log_level:8} ({process}) | {content.strip()}"
        
        # 尝试匹配通用格式 时间戳 | 级别 | 消息
        match = log_pattern2.match(line)
        if match:
            timestamp, log_level, content = match.groups()
            
            # 根据过滤条件决定是否显示
            if not should_display_log(line, log_level):
                return None
            
            # 简化格式，不显示时间戳
            if simple:
                level_style = log_level_styles.get(log_level, '')
                if level_style:
                    return f"[{level_style}]{log_level:8}[/{level_style}] | {content}"
                else:
                    return f"{log_level:8} | {content}"
            else:
                level_style = log_level_styles.get(log_level, '')
                if level_style:
                    return f"[dim]{timestamp}[/dim] | [{level_style}]{log_level:8}[/{level_style}] | {content}"
                else:
                    return f"[dim]{timestamp}[/dim] | {log_level:8} | {content}"
        
        # 对于不匹配任何模式的行，也进行关键字过滤
        if not should_display_log(line):
            return None
            
        return line
    
    # 构建描述过滤条件的文本
    filter_description = []
    if filter:
        filter_description.append(f"keyword: '[bold]{filter}[/bold]'")
    if level:
        filter_description.append(f"minimum level: '[bold]{level}[/bold]'")
    
    filter_text = f" (Filtered by {' and '.join(filter_description)})" if filter_description else ""
    format_text = " [dim](Raw format)[/dim]" if raw else " [dim](Simple format)[/dim]" if simple else ""
    
    if follow:
        console.print(Panel(
            f"Showing real-time logs from [bold]{log_file}[/bold]{filter_text}{format_text}\nPress Ctrl+C to exit",
            border_style="blue"
        ))
        try:
            # 使用subprocess.Popen执行tail -f命令来实时跟踪日志
            process = subprocess.Popen(
                ['tail', '-f', '-n', str(lines), log_file], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # 循环读取输出直到用户中断
            try:
                for line in process.stdout:
                    formatted_line = format_log_line(line)
                    if formatted_line:  # 如果行应该被显示
                        console.print(formatted_line)
            except KeyboardInterrupt:
                # 用户按下Ctrl+C，优雅地退出
                process.terminate()
                console.print("\n[yellow]Stopped following log file[/yellow]")
                return
            finally:
                # 确保进程被终止
                process.terminate()
                process.wait()
                
        except FileNotFoundError:
            console.print("[red]Error: 'tail' command not found. Cannot follow logs.[/red]")
            return
    else:
        # 原有的非实时日志显示逻辑
        console.print(Panel(
            f"Showing last {lines} lines from [bold]{log_file}[/bold]{filter_text}{format_text}", 
            border_style="blue"
        ))
        try:
            # Use tail for efficiency
            result = subprocess.run(['tail', '-n', str(lines), log_file], capture_output=True, text=True)
            if result.returncode == 0:
                displayed_count = 0
                for line in result.stdout.splitlines():
                    formatted_line = format_log_line(line)
                    if formatted_line:  # 如果行应该被显示
                        console.print(formatted_line)
                        displayed_count += 1
                
                # 如果过滤后没有显示任何内容，给出提示
                if displayed_count == 0 and (filter or level):
                    console.print("[yellow]No log entries match your filter criteria.[/yellow]")
            else:
                console.print(f"[red]Error reading log file: {result.stderr}[/red]")
        except FileNotFoundError:
            console.print("[red]Error: 'tail' command not found. Reading file directly.[/red]")
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
                displayed_count = 0
                for line in log_lines[-lines:]:
                    formatted_line = format_log_line(line)
                    if formatted_line:  # 如果行应该被显示
                        console.print(formatted_line)
                        displayed_count += 1
                
                # 如果过滤后没有显示任何内容，给出提示
                if displayed_count == 0 and (filter or level):
                    console.print("[yellow]No log entries match your filter criteria.[/yellow]")


@scheduler.command('status')
@click.pass_context
def show_tasks_status(ctx):
    """显示所有调度任务的状态"""
    from datetime import datetime
    from rich.console import Console
    from rich.table import Table
    from puti.db.schedule_manager import ScheduleManager

    console = ctx.obj.get('console', Console())
    manager = ctx.obj['manager']
    
    try:
        tasks = manager.get_all()
        
        if not tasks:
            console.print("[yellow]No scheduled tasks found.[/yellow]")
            return
            
        # 创建状态表格
        table = Table(title="Scheduled Tasks Status")
        
        # 添加列
        table.add_column("ID", style="dim")
        table.add_column("Name", style="green")
        table.add_column("Schedule", style="blue")
        table.add_column("Type", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Last Run", style="magenta")
        table.add_column("Next Run", style="yellow")
        table.add_column("PID", style="dim")
        
        now = datetime.now()
        
        # 添加任务行
        for task in tasks:
            # 确定状态
            if task.is_del:
                status = "[red]Deleted[/red]"
            elif not task.enabled:
                status = "[gray]Disabled[/gray]"
            elif task.is_running:
                status = "[bright_green]Running[/bright_green]"
            else:
                status = "[white]Ready[/white]"
                
            # 格式化上次运行时间
            if task.last_run:
                last_run = task.last_run.strftime('%Y-%m-%d %H:%M')
                time_ago = (now - task.last_run).total_seconds() / 60
                if time_ago < 60:
                    last_run = f"{last_run} ({int(time_ago)}m ago)"
                else:
                    hours = int(time_ago / 60)
                    last_run = f"{last_run} ({hours}h ago)"
            else:
                last_run = "[dim]Never[/dim]"
                
            # 格式化下次运行时间
            if task.next_run:
                if task.next_run > now:
                    time_to = (task.next_run - now).total_seconds() / 60
                    if time_to < 60:
                        next_run = f"{task.next_run.strftime('%H:%M')} (in {int(time_to)}m)"
                    else:
                        hours = int(time_to / 60)
                        next_run = f"{task.next_run.strftime('%H:%M')} (in {hours}h)"
                else:
                    next_run = f"{task.next_run.strftime('%H:%M')} [red](overdue)[/red]"
            else:
                next_run = "[dim]Unknown[/dim]"
                
            # 添加行
            table.add_row(
                str(task.id),
                task.name,
                task.cron_schedule,
                task.task_type_display,
                status,
                last_run,
                next_run,
                str(task.pid) if task.pid else "[dim]-[/dim]"
            )
            
        # 显示表格
        console.print(table)
        console.print(f"\nTotal: {len(tasks)} tasks")
        
        # 显示当前时间
        console.print(f"[dim]Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error fetching task status: {str(e)}[/red]")


@scheduler.command('reset')
@click.option('--id', 'task_id', type=int, help="Reset specific task by ID")
@click.option('--all', 'reset_all', is_flag=True, help="Reset all stuck tasks")
@click.option('--force', is_flag=True, help="Force reset even if task is not stuck")
@click.option('--minutes', type=int, default=30, help="Minutes threshold for stuck tasks (default: 30)")
@click.pass_context
def reset_tasks(ctx, task_id, reset_all, force, minutes):
    """重置卡住的调度任务"""
    from rich.console import Console
    from puti.db.schedule_manager import ScheduleManager
    
    console = ctx.obj.get('console', Console())
    manager = ctx.obj['manager']
    
    try:
        if task_id and force:
            # 强制重置指定的任务
            task = manager.get_by_id(task_id)
            if not task:
                console.print(f"[red]Error: Task with ID {task_id} not found[/red]")
                return
                
            manager.update(task_id, {"is_running": False, "pid": None})
            console.print(f"[green]✓ Task '{task.name}' (ID: {task_id}) has been forcefully reset[/green]")
            return
            
        if task_id:
            # 重置指定的任务，但仅当它卡住时
            task = manager.get_by_id(task_id)
            if not task:
                console.print(f"[red]Error: Task with ID {task_id} not found[/red]")
                return
                
            if not task.is_running:
                console.print(f"[yellow]Task '{task.name}' is not running. Use --force to reset anyway.[/yellow]")
                return
                
            from datetime import datetime, timedelta
            now = datetime.now()
            if force or not task.updated_at or (now - task.updated_at > timedelta(minutes=minutes)):
                manager.update(task_id, {"is_running": False, "pid": None})
                console.print(f"[green]✓ Task '{task.name}' (ID: {task_id}) has been reset[/green]")
            else:
                console.print(f"[yellow]Task '{task.name}' does not appear to be stuck (last update: {task.updated_at})[/yellow]")
            return
            
        if reset_all or force:
            # 重置所有卡住的任务
            reset_count = manager.reset_stuck_tasks(max_minutes=minutes)
            if reset_count > 0:
                console.print(f"[green]✓ {reset_count} stuck tasks have been reset[/green]")
            else:
                console.print(f"[yellow]No stuck tasks found.[/yellow]")
            return
            
        # 如果没有提供选项，显示帮助
        console.print("[yellow]Please specify either --id, --all, or --force option.[/yellow]")
        console.print("Run 'puti scheduler reset --help' for more information.")
        
    except Exception as e:
        console.print(f"[red]Error resetting tasks: {str(e)}[/red]")


if __name__ == '__main__':
    main()
