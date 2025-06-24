import puti.bootstrap  # noqa: F401, must be the first import
import click
import asyncio
import questionary
import os
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from puti.llm.roles.agents import Alex, Ethan
from puti.core.config_setup import ensure_twikit_config_is_present

# 设置环境变量
if not os.environ.get('PUTI_DATA_PATH'):
    data_path = os.path.expanduser('~/puti/data')
    os.makedirs(data_path, exist_ok=True)
    os.environ['PUTI_DATA_PATH'] = data_path
    print(f"Set PUTI_DATA_PATH to {data_path}")


@click.group()
def main():
    """Puti CLI Tool: An interactive AI assistant."""
    # ensure_config_is_present()
    pass


@main.command()
@click.option('--name', default='Puti', help='Name to greet.')
def hello(name):
    """Greets the user."""
    click.echo(f"Hello, {name}!")


@main.command()
@click.option('--name', default='Alex', help='Name of the Alex agent.')
def alex_chat(name):
    """Starts an interactive chat with Alex agent."""
    console = Console()
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
                # user_input = 'hi'
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
    console = Console()
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
    
    # 如果计划正在运行，先停止它
    if schedule.is_running:
        manager.stop_task(schedule_id)
        console.print(f"[yellow]Stopped running task for schedule '{schedule.name}'.[/yellow]")
    
    # 删除计划
    if manager.delete_schedule(schedule_id):
        console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) has been deleted.[/green]")
    else:
        console.print(f"[red]Failed to delete schedule '{schedule.name}' (ID: {schedule_id}).[/red]")


@scheduler.command()
@click.argument('schedule_id', type=int)
def run(schedule_id):
    """手动运行特定计划任务。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    # 对于已禁用的计划显示警告
    if not schedule.enabled:
        console.print(f"[yellow]Warning: Schedule '{schedule.name}' is currently disabled.[/yellow]")
        confirm = click.confirm("Do you want to run it anyway?", default=True)
        if not confirm:
            return
    
    # 对于正在运行的计划显示警告
    if schedule.is_running:
        console.print(f"[yellow]Warning: Schedule '{schedule.name}' is already running.[/yellow]")
        confirm = click.confirm("Do you want to run another instance?", default=False)
        if not confirm:
            return
    
    # 启动任务
    console.print(f"[green]Starting task for schedule '{schedule.name}'...[/green]")
    
    try:
        from celery_queue.simplified_tasks import execute_twitter_bot_task
        task = execute_twitter_bot_task.delay(schedule_id)
        console.print(f"[green]Task started with ID: {task.id}[/green]")
        console.print("Use 'puti scheduler logs' to monitor task progress.")
    except Exception as e:
        console.print(f"[red]Error starting task:[/red] {str(e)}")


@scheduler.command()
def logs():
    """View the scheduler logs."""
    from puti.scheduler import get_default_log_dir
    from rich.console import Console
    import subprocess
    
    console = Console()
    log_path = get_default_log_dir() / 'scheduler_beat.log'
    
    if not log_path.exists():
        console.print(f"[yellow]Log file not found: {log_path}[/yellow]")
        return
    
    # Use subprocess to tail the log file
    try:
        console.print(f"[cyan]Showing recent logs from {log_path}[/cyan]")
        subprocess.run(['tail', '-n', '50', '-f', str(log_path)], check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Log viewing stopped.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error viewing logs: {str(e)}[/red]")


@scheduler.command()
def workers():
    """Check the status of Celery workers."""
    import subprocess
    from rich.console import Console
    
    console = Console()
    console.print("[cyan]Checking Celery worker status...[/cyan]")
    
    try:
        # Run celery inspect command to get active workers
        result = subprocess.run(
            ['celery', '-A', 'celery_queue.celery_app', 'inspect', 'active', '--timeout', '5'],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        if "No nodes replied within time constraint" in result.stdout:
            console.print("[yellow]No Celery workers are currently running.[/yellow]")
            return
            
        if result.returncode != 0:
            console.print(f"[red]Error running Celery inspect command: {result.stderr}[/red]")
            return
            
        console.print(result.stdout)
        
        # Also show registered tasks
        console.print("\n[cyan]Registered tasks:[/cyan]")
        task_result = subprocess.run(
            ['celery', '-A', 'celery_queue.celery_app', 'inspect', 'registered', '--timeout', '5'],
            capture_output=True,
            text=True,
            check=False
        )
        console.print(task_result.stdout)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


@scheduler.command()
def tasks():
    """Show task execution statistics."""
    from puti.db.base_manager import BaseManager
    from puti.db.model.task.bot_task import TweetSchedule
    from rich.console import Console
    from rich.table import Table
    from celery_queue.celery_app import app
    import time
    
    console = Console()
    
    # Get active schedules
    schedule_manager = BaseManager(model_type=TweetSchedule)
    active_schedules = schedule_manager.get_all(where_clause="enabled = 1")
    
    # Get active tasks from Celery
    try:
        i = app.control.inspect()
        active_tasks = i.active()
        scheduled_tasks = i.scheduled()
        reserved_tasks = i.reserved()
        
        # Create active tasks table
        if active_tasks:
            console.print("\n[bold cyan]Currently Executing Tasks:[/bold cyan]")
            active_table = Table()
            active_table.add_column("Worker", style="cyan")
            active_table.add_column("Task ID", style="dim")
            active_table.add_column("Task Name", style="green")
            active_table.add_column("Started", style="magenta")
            active_table.add_column("Runtime", style="blue")
            
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    name = task.get('name', 'Unknown')
                    task_id = task.get('id', 'Unknown')
                    started = time.strftime('%Y-%m-%d %H:%M:%S', 
                                            time.localtime(task.get('time_start', 0)))
                    runtime = f"{task.get('runtime', 0):.2f}s" if 'runtime' in task else 'N/A'
                    
                    active_table.add_row(
                        worker,
                        task_id,
                        name,
                        started,
                        runtime
                    )
            console.print(active_table)
        else:
            console.print("[yellow]No tasks are currently being executed.[/yellow]")
        
        # Create scheduled tasks table
        console.print("\n[bold cyan]Scheduled Tasks:[/bold cyan]")
        schedule_table = Table(title="Tasks scheduled by Celery Beat")
        schedule_table.add_column("ID", style="dim")
        schedule_table.add_column("Name", style="cyan")
        schedule_table.add_column("Cron Schedule", style="green")
        schedule_table.add_column("Next Run", style="magenta")
        schedule_table.add_column("Parameters", style="blue")
        
        for schedule in active_schedules:
            next_run = schedule.next_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.next_run else "Never"
            params_str = ", ".join(f"{k}={v}" for k, v in schedule.params.items()) if schedule.params else "None"
            
            schedule_table.add_row(
                str(schedule.id),
                schedule.name,
                schedule.cron_schedule,
                next_run,
                params_str
            )
        
        console.print(schedule_table)
        
    except Exception as e:
        console.print(f"[red]Error getting task information: {str(e)}[/red]")
        console.print("[yellow]Make sure Celery workers are running.[/yellow]")


@scheduler.command()
@click.argument('schedule_id', type=int)
def inspect(schedule_id):
    """Show detailed information about a specific schedule."""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.json import JSON
    import json
    from datetime import datetime
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    # Format times for display
    created_at = schedule.created_at.strftime("%Y-%m-%d %H:%M:%S") if schedule.created_at else "Unknown"
    updated_at = schedule.updated_at.strftime("%Y-%m-%d %H:%M:%S") if schedule.updated_at else "Unknown"
    next_run = schedule.next_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.next_run else "Never"
    last_run = schedule.last_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.last_run else "Never"
    
    # Calculate time until next run
    time_until = ""
    if schedule.next_run:
        delta = schedule.next_run - datetime.now()
        if delta.total_seconds() > 0:
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            seconds = delta.seconds % 60
            time_until = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            time_until = "Overdue"
    
    # Pretty format parameters
    params_json = json.dumps(schedule.params, indent=2) if schedule.params else "{}"
    
    # Determine running status
    running_status = "🟢 Running" if schedule.is_running else "🔴 Not Running"
    pid_status = f"PID: {schedule.pid}" if schedule.pid else "No PID"
    task_id_status = f"Task ID: {schedule.task_id}" if schedule.task_id else "No Task ID"
    
    # Check if process is actually running if we have a PID
    process_status = ""
    if schedule.pid:
        try:
            os.kill(schedule.pid, 0)
            process_status = "[green]Process verified running[/green]"
        except OSError:
            process_status = "[yellow]Process not found (stale PID)[/yellow]"
    
    # Build detailed markdown report
    details = f"""
# Schedule: {schedule.name} (ID: {schedule.id})

## Basic Information
- **Status**: {'🟢 Enabled' if schedule.enabled else '🔴 Disabled'}
- **Cron Schedule**: `{schedule.cron_schedule}`
- **Created**: {created_at}
- **Last Updated**: {updated_at}

## Execution Information
- **Last Run**: {last_run}
- **Next Run**: {next_run}
- **Time Until Next Run**: {time_until}

## Running Status
- **Is Running**: {running_status}
- **{pid_status}**
- **{task_id_status}**
{process_status}

## Parameters
"""
    
    console.print(Panel(Markdown(details), title="Schedule Details", border_style="cyan"))
    console.print(Panel(JSON(params_json), title="Parameters", border_style="green"))
    
    # Show command help for managing this schedule
    commands = f"""
To manage this schedule, you can use the following commands:

1. Start the task:
   `puti scheduler start_task {schedule.id}`

2. Stop the task:
   `puti scheduler stop_task {schedule.id}`

3. Enable/Disable the schedule:
   `puti scheduler toggle {schedule.id} --enable`
   `puti scheduler toggle {schedule.id} --disable`
    """
    
    console.print(Panel(Markdown(commands), title="Commands", border_style="yellow"))


@scheduler.command()
def alias():
    """Show the mapping between puti scheduler commands and puti-cmd commands."""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    table = Table(title="Command Mapping")
    table.add_column("puti scheduler", style="cyan")
    table.add_column("puti-cmd", style="green")
    table.add_column("Description", style="yellow")
    
    table.add_row("start", "start", "Start the scheduler daemon")
    table.add_row("stop", "stop", "Stop the scheduler daemon")
    table.add_row("status", "status", "Check scheduler status")
    table.add_row("list", "list", "List scheduled tasks")
    table.add_row("create", "create", "Create/update a schedule")
    table.add_row("toggle --enable", "enable", "Enable a schedule")
    table.add_row("toggle --disable", "disable", "Disable a schedule")
    table.add_row("delete", "delete", "Delete a schedule")
    table.add_row("run", "run", "Manually run a task")
    
    console.print(table)
    console.print("\n[bold yellow]Note:[/bold yellow] You can use either command set based on your preference.")


# Add the scheduler group to the main CLI
main.add_command(scheduler)

if __name__ == "__main__":
    main()
