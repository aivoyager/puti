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
import re
from typing import Optional, Dict, Any, List
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from puti.core.config_setup import ensure_twikit_config_is_present
from puti.db.schedule_manager import ScheduleManager
from puti.scheduler import ensure_worker_running, ensure_beat_running, WorkerDaemon, BeatDaemon
from puti.llm.roles.agents import Alex, Ethan
from puti.constant.base import Pathh

# Create a global console instance
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
        title="[bold magenta]🤖 Meet Alex[/bold magenta]",
        subtitle="Your friendly, all-purpose AI assistant",
        border_style="magenta",
        padding=(1, 2)
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
*   Press `Ctrl+D` or `Ctrl+C` to exit immediately.
""")
    console.print(welcome_message)
    console.rule("[bold yellow]Chat Session Started[/bold yellow]")

    alex_agent = Alex(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await questionary.text("👤 You:", qmark=">>>").ask_async()
                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                console.print(Panel(
                    user_input,
                    title="[b]👤 You[/b]",
                    border_style="bright_blue",
                    padding=(1, 2),
                    title_align="left"
                ))

                # Show a thinking indicator
                with console.status(f"[bold magenta]{name} is thinking...", spinner="dots"):
                    response = await alex_agent.run(user_input)

                # Print the response in a styled panel
                response_panel = Panel(
                    Markdown(response),
                    title=f"[b]🤖 {name}[/b]",
                    border_style="magenta",
                    title_align="right",
                    padding=(1, 2)
                )
                console.print(response_panel)

            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C and Ctrl+D
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print(Panel("[bold yellow]Chat session ended. Goodbye! 👋[/bold yellow]", box=box.ROUNDED, border_style="yellow"))


@main.command()
@click.option('--name', default='Ethan', help='Name of the Ethan agent.')
def ethan_chat(name):
    """Starts an interactive chat with Ethan agent."""
    ensure_twikit_config_is_present()
    console.print(Panel(
        Markdown("""
```
(-_o)
```
Ethan is a Twitter bot designed to help you manage your daily Twitter activities.
"""),
        title="[bold cyan]Meet Ethan, the X-Bot[/bold cyan]",
        subtitle="Your witty companion for the X-verse",
        border_style="cyan",
        padding=(1, 2)
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
*   Press `Ctrl+D` or `Ctrl+C` to exit immediately.
""")
    console.print(welcome_message)
    console.rule("[bold yellow]Chat Session Started[/bold yellow]")

    ethan_agent = Ethan(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await questionary.text("👤 You:", qmark=">>>").ask_async()
                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                console.print(Panel(
                    user_input,
                    title="[b]👤 You[/b]",
                    border_style="bright_blue",
                    padding=(1, 2),
                    title_align="left"
                ))

                with console.status(f"[bold cyan]{name} is thinking...", spinner="dots"):
                    response = await ethan_agent.run(user_input)

                response_panel = Panel(
                    Markdown(response),
                    title=f"[b](-_o) {name}[/b]",
                    border_style="cyan",
                    title_align="right",
                    padding=(1, 2)
                )
                console.print(response_panel)

            except (KeyboardInterrupt, EOFError):
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print(Panel("[bold yellow]Chat session ended. Goodbye! 👋[/bold yellow]", box=box.ROUNDED, border_style="yellow"))


@main.command()
@click.option('--id', required=True, help='Tweet ID to reply to with context awareness.')
@click.option('--depth', default=5, help='Maximum depth for tracing conversation history.')
def context_aware_reply(id, depth):
    """Reply to a specific tweet with full conversation context awareness."""
    ensure_twikit_config_is_present()
    
    from puti.llm.roles.agents import Ethan
    from puti.llm.actions.x_bot import ContextAwareReplyAction
    
    console.print(Panel(
        f"Preparing to reply to tweet ID: {id} with context awareness (max depth: {depth})",
        title="🤖 Ethan Context-Aware Reply",
        border_style="cyan"
    ))
    
    ethan_agent = Ethan(name="Ethan")
    action = ContextAwareReplyAction(tweet_id=id, max_context_depth=depth)
    
    async def run_reply():
        with console.status("[bold cyan]Analyzing conversation context...", spinner="dots"):
            result = await action.run(ethan_agent)
        
        if hasattr(result, 'is_success') and result.is_success():
            console.print(Panel(
                f"✅ [bold green]Successfully sent context-aware reply![/bold green]\n\n{result.data}",
                title="Reply Status",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"❌ [bold red]Failed to send reply[/bold red]\n\n{result}",
                title="Reply Status",
                border_style="red"
            ))
    
    asyncio.run(run_reply())


@main.command()
@click.option('--days', default=7, help='Number of days to look back for unreplied mentions.')
@click.option('--hours', default=None, help='Number of hours to look back for unreplied mentions. Takes precedence over days if both are specified.')
@click.option('--depth', default=5, help='Maximum depth for tracing conversation history.')
@click.option('--max', default=5, help='Maximum number of mentions to process.')
def reply_to_mentions(days, hours, depth, max):
    """Find unreplied mentions and reply with full conversation context awareness."""
    ensure_twikit_config_is_present()
    
    from puti.llm.roles.agents import Ethan
    from puti.llm.actions.x_bot import ContextAwareReplyToMentionsAction
    
    # Determine time unit and value
    time_unit = 'days'
    time_value = days
    
    if hours is not None:
        time_unit = 'hours'
        time_value = hours
    
    console.print(Panel(
        f"Finding unreplied mentions from the last {time_value} {time_unit} and replying with context awareness (max depth: {depth})",
        title="🤖 Ethan Context-Aware Reply to Mentions",
        border_style="cyan"
    ))
    
    ethan_agent = Ethan(name="Ethan")
    action = ContextAwareReplyToMentionsAction(
        time_value=time_value,
        time_unit=time_unit,
        max_context_depth=depth,
        max_mentions=max
    )
    
    async def run_reply_to_mentions():
        with console.status("[bold cyan]Finding and processing mentions...", spinner="dots"):
            result = await action.run(ethan_agent)
        
        console.print(Panel(
            f"[bold]Results:[/bold]\n\n{result}",
            title="Process Summary",
            border_style="green"
        ))
    
    asyncio.run(run_reply_to_mentions())


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
    from datetime import datetime
    
    console = ctx.obj.get('console', Console())
    manager = ScheduleManager()
    tasks = manager.get_all(where_clause="is_del = 0")

    table = Table(title="Scheduled Tasks", border_style="cyan")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Name", style="bold")
    table.add_column("Enabled", justify="center")
    table.add_column("Task Type")
    table.add_column("CRON")
    table.add_column("Next Run", style="yellow")
    table.add_column("Params")
    
    now = datetime.now()

    for task in tasks:
        enabled_str = "[green]Yes[/green]" if task.enabled else "[red]No[/red]"
        
        # Format next run time
        if task.next_run:
            if task.next_run > now:
                time_to = (task.next_run - now).total_seconds() / 60
                if time_to < 60:
                    next_run_str = f"{task.next_run.strftime('%H:%M:%S')} (in {int(time_to)}m)"
                else:
                    hours = int(time_to / 60)
                    next_run_str = f"{task.next_run.strftime('%H:%M:%S')} (in {hours}h)"
            else:
                next_run_str = f"{task.next_run.strftime('%H:%M:%S')} [red](overdue)[/red]"
        else:
            next_run_str = "[dim]N/A[/dim]"

        table.add_row(
            str(task.id),
            task.name,
            enabled_str,
            task.task_type_display,
            task.cron_schedule,
            next_run_str,
            str(task.params)
        )
    
    console.print(table)
    

@scheduler.command('create')
@click.argument('name')
@click.argument('cron')
@click.option('--type', 'task_type', required=True, 
              help="任务类型，可选值：'post'(发布推文), 'reply'(回复推文), 'context_reply'(上下文感知回复)")
@click.option('--params', 
              help="任务参数的 JSON 字符串。不同任务类型需要不同参数，详见文档。例如：'post' 类型需要 '{\"topic\": \"AI技术\"}'", 
              default='{}')
@click.pass_context
def create_task(ctx, name, cron, task_type, params):
    """创建新的定时任务（默认为禁用状态）。
    
    参数:
      NAME    任务的唯一名称，用于在列表和日志中标识任务
      CRON    标准 cron 表达式，定义任务执行时间表，格式：'分 时 日 月 周'
    
    常用 cron 示例:
      "0 12 * * *"    - 每天中午12点
      "0 */3 * * *"   - 每3小时执行一次
      "0 9 * * 1-5"   - 工作日上午9点
      "*/30 * * * *"  - 每30分钟执行一次
    
    任务类型及参数示例:
      post: 发布推文
        --params '{"topic": "AI技术"}'
      
      reply: 回复推文
        --params '{"time_value": 24, "time_unit": "hours"}'
      
      context_reply: 上下文感知回复
        --params '{"time_value": 24, "time_unit": "hours", "max_mentions": 3}'
    
    注意: 新创建的任务默认为禁用状态，需要使用 'puti scheduler enable TASK_ID' 来启用。
    详细文档: docs/proj/scheduler_create_command.md
    """
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
        console.print(f"[green]✓ 任务 '{name}' 创建成功，ID: {task.id}[/green]")
        console.print(f"[yellow]提示: 使用 'puti scheduler enable {task.id}' 来启用此任务[/yellow]")
    except json.JSONDecodeError:
        console.print("[red]错误: --params 的 JSON 字符串格式无效。请确保使用双引号包裹键名，例如: '{\"key\": \"value\"}'[/red]")
    except Exception as e:
        console.print(f"[red]创建任务时出错: {str(e)}[/red]")


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
    
    # Determine the log file path based on the selected service
    if service == 'worker':
        log_file = Pathh.WORKER_LOG.val
    elif service == 'beat':
        log_file = Pathh.BEAT_LOG.val
    elif service == 'scheduler':
        # The scheduler log is actually scheduler_beat.log
        log_file = str(Path(Pathh.CONFIG_DIR.val) / 'logs' / 'scheduler_beat.log')
    
    if not os.path.exists(log_file):
        console.print(f"[red]Log file not found at: {log_file}[/red]")
        return
    
    # Define style mapping and priority for log levels
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
    
    # Regex patterns for different log formats
    # 1. Standard format: [2025-06-25 12:00:32,330: WARNING/MainProcess]
    log_pattern1 = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}): (\w+)/(.+)\](.+)')
    # 2. General format: 2023-01-01 13:45:01,123 | DEBUG | message
    log_pattern2 = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| (\w+)\s+ \| (.+)')
    
    def should_display_log(line, log_level=None):
        """Decide whether to display a log line based on filtering conditions."""
        # Keyword filtering
        if filter and filter.lower() not in line.lower():
            return False
            
        # Log level filtering
        if level and log_level:
            log_priority = log_level_priority.get(log_level, 0)
            if log_priority < min_level_priority:
                return False
                
        return True
    
    def format_log_line(line):
        """Format the log line, adding color and style."""
        line = line.strip()
        
        # If using raw output, only filter, do not format
        if raw:
            return None if not should_display_log(line) else line
        
        # Try to match standard format [timestamp: level/process]
        match = log_pattern1.match(line)
        if match:
            timestamp, log_level, process, content = match.groups()
            
            # Decide whether to display based on filtering conditions
            if not should_display_log(line, log_level):
                return None
            
            # Simplified format, no timestamp
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
        
        # Try to match general format: timestamp | level | message
        match = log_pattern2.match(line)
        if match:
            timestamp, log_level, content = match.groups()
            
            # Decide whether to display based on filtering conditions
            if not should_display_log(line, log_level):
                return None
            
            # Simplified format, no timestamp
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
        
        # For lines that do not match any pattern, also perform keyword filtering
        if not should_display_log(line):
            return None
            
        return line
    
    # Build text describing the filtering conditions
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
            # Use subprocess.Popen to execute tail -f for real-time log tracking
            process = subprocess.Popen(
                ['tail', '-f', '-n', str(lines), log_file], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Loop to read output until user interrupts
            try:
                for line in process.stdout:
                    formatted_line = format_log_line(line)
                    if formatted_line:  # If the line should be displayed
                        console.print(formatted_line)
            except KeyboardInterrupt:
                # User pressed Ctrl+C, exit gracefully
                process.terminate()
                console.print("\n[yellow]Stopped following log file[/yellow]")
                return
            finally:
                # Ensure the process is terminated
                process.terminate()
                process.wait()
                
        except FileNotFoundError:
            console.print("[red]Error: 'tail' command not found. Cannot follow logs.[/red]")
            return
    else:
        # Original logic for non-real-time log display
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
                    if formatted_line:  # If the line should be displayed
                        console.print(formatted_line)
                        displayed_count += 1
                
                # If nothing is displayed after filtering, provide a hint
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
                    if formatted_line:  # If the line should be displayed
                        console.print(formatted_line)
                        displayed_count += 1
                
                # If nothing is displayed after filtering, provide a hint
                if displayed_count == 0 and (filter or level):
                    console.print("[yellow]No log entries match your filter criteria.[/yellow]")


@scheduler.command('status')
@click.pass_context
def show_tasks_status(ctx):
    """Shows the status of all scheduled tasks."""
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
            
        # Create a status table
        table = Table(title="Scheduled Tasks Status")
        
        # Add columns
        table.add_column("ID", style="dim")
        table.add_column("Name", style="green")
        table.add_column("Schedule", style="blue")
        table.add_column("Type", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Last Run", style="magenta")
        table.add_column("Next Run", style="yellow")
        table.add_column("PID", style="dim")
        
        now = datetime.now()
        
        # Add task rows
        for task in tasks:
            # Determine status
            if task.is_del:
                status = "[red]Deleted[/red]"
            elif not task.enabled:
                status = "[gray]Disabled[/gray]"
            elif task.is_running:
                status = "[bright_green]Running[/bright_green]"
            else:
                status = "[white]Ready[/white]"
                
            # Format last run time
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
                
            # Format next run time
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
                
            # Add a row
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
            
        # Display the table
        console.print(table)
        console.print(f"\nTotal: {len(tasks)} tasks")
        
        # Display the current time
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
    """Resets stuck scheduled tasks."""
    from rich.console import Console
    from puti.db.schedule_manager import ScheduleManager
    
    console = ctx.obj.get('console', Console())
    manager = ctx.obj['manager']
    
    try:
        if task_id and force:
            # Forcefully reset the specified task
            task = manager.get_by_id(task_id)
            if not task:
                console.print(f"[red]Error: Task with ID {task_id} not found[/red]")
                return
                
            manager.update(task_id, {"is_running": False, "pid": None})
            console.print(f"[green]✓ Task '{task.name}' (ID: {task_id}) has been forcefully reset[/green]")
            return
            
        if task_id:
            # Reset the specified task, but only if it's stuck
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
            # Reset all stuck tasks
            reset_count = manager.reset_stuck_tasks(max_minutes=minutes)
            if reset_count > 0:
                console.print(f"[green]✓ {reset_count} stuck tasks have been reset[/green]")
            else:
                console.print(f"[yellow]No stuck tasks found.[/yellow]")
            return
            
        # If no option is provided, show help
        console.print("[yellow]Please specify either --id, --all, or --force option.[/yellow]")
        console.print("Run 'puti scheduler reset --help' for more information.")
        
    except Exception as e:
        console.print(f"[red]Error resetting tasks: {str(e)}[/red]")


@scheduler.command('refresh')
@click.option('--worker/--no-worker', default=True, help="Whether to refresh the Celery worker")
@click.option('--beat/--no-beat', default=True, help="Whether to refresh the Celery beat scheduler")
@click.option('--force', is_flag=True, help="Force kill processes if they don't stop gracefully")
@click.pass_context
def refresh_services(ctx, worker, beat, force):
    """Refresh (restart) worker and/or beat processes to load code changes."""
    from puti.constant.base import Pathh
    from puti.scheduler import WorkerDaemon, BeatDaemon
    
    console = ctx.obj.get('console', Console())
    
    if worker:
        worker_daemon = WorkerDaemon(name='worker', pid_file=Pathh.WORKER_PID.val, log_file=Pathh.WORKER_LOG.val)
        console.print(Panel(Markdown("Refreshing Celery worker..."), border_style="yellow"))
        
        # Stop worker if running
        if worker_daemon.is_running():
            console.print("[yellow]Stopping Celery worker...[/yellow]")
            if worker_daemon.stop(force=force):
                console.print("[green]✓ Worker stopped successfully[/green]")
            else:
                console.print("[red]✗ Failed to stop worker[/red]")
                if not force:
                    console.print("[yellow]Tip: Try again with --force option to force kill the process[/yellow]")
                    return
        else:
            console.print("[yellow]Celery worker is not running[/yellow]")
            
        # Start worker again
        console.print("[yellow]Starting Celery worker...[/yellow]")
        if worker_daemon.start():
            console.print("[green]✓ Worker started successfully[/green]")
        else:
            console.print("[red]✗ Failed to start worker. Check logs at: {}[/red]".format(worker_daemon.log_file))
            
    if beat:
        beat_daemon = BeatDaemon(name='beat', pid_file=Pathh.BEAT_PID.val, log_file=Pathh.BEAT_LOG.val)
        console.print(Panel(Markdown("Refreshing Celery beat (scheduler)..."), border_style="yellow"))
        
        # Stop beat if running
        if beat_daemon.is_running():
            console.print("[yellow]Stopping Celery beat...[/yellow]")
            if beat_daemon.stop(force=force):
                console.print("[green]✓ Beat stopped successfully[/green]")
            else:
                console.print("[red]✗ Failed to stop beat[/red]")
                if not force:
                    console.print("[yellow]Tip: Try again with --force option to force kill the process[/yellow]")
                    return
        else:
            console.print("[yellow]Celery beat is not running[/yellow]")
            
        # Start beat again
        console.print("[yellow]Starting Celery beat...[/yellow]")
        if beat_daemon.start():
            console.print("[green]✓ Beat started successfully[/green]")
        else:
            console.print("[red]✗ Failed to start beat. Check logs at: {}[/red]".format(beat_daemon.log_file))
            
    if worker and beat and worker_daemon.is_running() and beat_daemon.is_running():
        console.print(Panel(
            Markdown("✅ **Refresh completed successfully!**\nAll processes are now running with the latest code."),
            border_style="green"
        ))
    elif (worker and not beat and worker_daemon.is_running()) or (beat and not worker and beat_daemon.is_running()):
        console.print(Panel(
            Markdown("✅ **Partial refresh completed successfully!**\nSelected processes are running with the latest code."),
            border_style="green"
        ))
    else:
        console.print(Panel(
            Markdown("⚠️ **Refresh completed with errors!**\nSome processes may not be running correctly."),
            border_style="red"
        ))


if __name__ == '__main__':
    main()
