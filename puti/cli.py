import puti.bootstrap  # noqa: F401, must be the first import
import click
import asyncio
import questionary
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from puti.llm.roles.agents import Alex, Ethan
from puti.core.config_setup import ensure_twikit_config_is_present


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


@click.group()
def scheduler():
    """
    Manage tweet scheduler operations.
    
    This command group provides tools to:
    
    1. Start/stop the scheduler daemon
    2. Create and configure tweet schedules
    3. View task status and schedule information
    4. Monitor logs and worker activity
    """
    pass


@scheduler.command()
@click.option('--start-tasks/--no-start-tasks', default=True, 
              help="Whether to activate all enabled tasks when starting the daemon")
def start_daemon(start_tasks):
    """Start the scheduler daemon."""
    from puti.scheduler import SchedulerDaemon
    
    daemon = SchedulerDaemon()
    daemon.start(activate_tasks=start_tasks)


@scheduler.command()
def stop_daemon():
    """Stop the scheduler daemon."""
    from puti.scheduler import SchedulerDaemon
    from puti.db.base_manager import BaseManager
    from puti.db.model.task.bot_task import TweetSchedule
    
    # First, disable all enabled schedules in the database
    schedule_manager = BaseManager(model_type=TweetSchedule)
    for schedule in schedule_manager.get_all(where_clause="enabled = 1"):
        schedule_manager.update(schedule.id, {"enabled": False, "is_running": False, "pid": None})
    
    # Then, stop the scheduler daemon
    daemon = SchedulerDaemon()
    daemon.stop()


@scheduler.command()
@click.argument('name', required=True)
@click.argument('cron', required=True)
@click.option('--topic', '-t', help='Topic for tweet generation')
@click.option('--tags', '-g', help='Comma-separated list of tags for the tweet')
@click.option('--enabled/--disabled', default=True, help='Enable or disable this schedule')
@click.option('--start/--no-start', default=False, help='Start the task immediately after creation')
def set(name, cron, topic=None, tags=None, enabled=True, start=False):
    """
    Create or update a scheduled tweet task.
    
    Examples:
        puti scheduler set daily_tweet "0 12 * * *" --topic "AI News" --tags "ai,news,tech" 
        puti scheduler set weekend_tweet "0 18 * * 6,0" --topic "Weekend Tech" --disabled
    """
    from puti.db.schedule_manager import ScheduleManager
    from croniter import croniter
    import datetime
    
    # Validate cron expression
    try:
        now = datetime.datetime.now()
        next_run = croniter(cron, now).get_next(datetime.datetime)
    except ValueError:
        click.echo(f"Invalid cron expression: {cron}", err=True)
        return
    
    # Convert comma-separated tags to a list
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Set up parameters for the tweet generation
    params = {}
    if topic:
        params['topic'] = topic
    if tag_list:
        params['tags'] = tag_list
    
    # Save or update the schedule in the database
    manager = ScheduleManager()
    existing_schedule = manager.get_by_name(name)
    
    if existing_schedule:
        # Update existing schedule
        manager.update_schedule(existing_schedule.id, 
                              cron_schedule=cron,
                              enabled=enabled,
                              params=params)
        click.echo(f"Updated tweet schedule '{name}'")
    else:
        # Create new schedule
        schedule = manager.create_schedule(
            name=name,
            cron_schedule=cron,
            enabled=enabled,
            params=params
        )
        click.echo(f"Created tweet schedule '{name}' (ID: {schedule.id})")
    
    if enabled and start:
        # Start the task immediately if requested
        schedule = manager.get_by_name(name)
        if schedule:
            manager.start_task(schedule.id)
            click.echo(f"Started task for schedule '{name}'")
    elif enabled:
        # Trigger an immediate check to register the schedule with Celery Beat
        from celery_queue.simplified_tasks import check_dynamic_schedules
        check_dynamic_schedules.delay()
        click.echo("Triggered schedule registration")


@scheduler.command()
def daemon_status():
    """Check the status of the scheduler daemon."""
    from puti.scheduler import SchedulerDaemon
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    daemon = SchedulerDaemon()
    
    table = Table(title="Scheduler Daemon Status")
    table.add_column("Status", style="cyan")
    table.add_column("PID", style="green")
    
    if daemon.is_running():
        pid = daemon._get_pid()
        table.add_row("Running", str(pid))
    else:
        table.add_row("Stopped", "N/A")
    
    console.print(table)


@scheduler.command()
@click.option('--all', '-a', is_flag=True, help="Show all schedules including disabled ones")
@click.option('--running', '-r', is_flag=True, help="Show only currently running schedules")
def list(all, running):
    """List scheduled tasks."""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.table import Table
    import datetime
    
    console = Console()
    manager = ScheduleManager()
    
    # Get schedules from database based on filters
    if running:
        schedules = manager.get_running_schedules()
        title = "Currently Running Tasks"
    elif all:
        schedules = manager.get_all()
        title = "All Scheduled Tasks"
    else:
        schedules = manager.get_active_schedules()
        title = "Enabled Scheduled Tasks"
    
    if not schedules:
        console.print(f"[yellow]No schedules found matching the criteria.[/yellow]")
        return
    
    # Create a table to display the schedules
    table = Table(title=title)
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Cron Schedule", style="green")
    table.add_column("Next Run", style="magenta")
    table.add_column("Last Run", style="blue")
    table.add_column("Status", style="yellow")
    table.add_column("Running", style="bright_green")
    table.add_column("PID", style="bright_blue")
    
    now = datetime.datetime.now()
    
    for schedule in schedules:
        # Format dates for display
        next_run = schedule.next_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.next_run else "Never"
        last_run = schedule.last_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.last_run else "Never"
        
        # Determine status
        status = "Enabled" if schedule.enabled else "Disabled"
        running_status = "Yes" if schedule.is_running else "No"
        pid = str(schedule.pid) if schedule.pid else "N/A"
        
        table.add_row(
            str(schedule.id),
            schedule.name,
            schedule.cron_schedule,
            next_run,
            last_run,
            status,
            running_status,
            pid
        )
    
    console.print(table)


@scheduler.command()
@click.argument('schedule_id', type=int)
def start_task(schedule_id):
    """Start a specific task by schedule ID."""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    if not schedule.enabled:
        console.print(f"[yellow]Warning:[/yellow] Enabling disabled schedule '{schedule.name}' before starting.")
        manager.update_schedule(schedule_id, enabled=True)
    
    result = manager.start_task(schedule_id)
    if result:
        console.print(f"[green]Task for schedule '{schedule.name}' started.[/green]")
    else:
        console.print(f"[red]Failed to start task for schedule '{schedule.name}'.[/red]")


@scheduler.command()
@click.argument('schedule_id', type=int)
def stop_task(schedule_id):
    """Stop a specific task by schedule ID."""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    result = manager.stop_task(schedule_id)
    if result:
        console.print(f"[green]Task for schedule '{schedule.name}' stopped.[/green]")
    else:
        console.print(f"[red]Failed to stop task for schedule '{schedule.name}'.[/red]")


@scheduler.command()
@click.argument('schedule_id', type=int)
@click.option('--enable/--disable', default=True, help="Enable or disable the schedule")
def toggle(schedule_id, enable):
    """Enable or disable a schedule by ID."""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    manager.update_schedule(schedule_id, enabled=enable)
    status = "enabled" if enable else "disabled"
    console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) {status}.[/green]")
    
    # If enabling, trigger an immediate check
    if enable:
        from celery_queue.simplified_tasks import check_dynamic_schedules
        check_dynamic_schedules.delay()
        console.print("[green]Triggered an immediate schedule check.[/green]")


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
    import os
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
@click.argument('schedule_id', type=int)
def delete(schedule_id):
    """Delete a schedule by ID."""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    # Stop the task if it's running
    if schedule.is_running:
        manager.stop_task(schedule_id)
    
    # Delete the schedule (use hard delete to actually remove it)
    result = manager.delete(schedule_id, soft_delete=False)
    if result:
        console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) has been deleted.[/green]")
    else:
        console.print(f"[red]Failed to delete schedule '{schedule.name}'.[/red]")


@scheduler.command()
@click.argument('schedule_id', type=int)
def run(schedule_id):
    """
    Manually run a specific scheduled task.
    
    This will execute the task immediately, regardless of its scheduled time.
    The task's last_run time will be updated, but the schedule itself won't be modified.
    """
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    import datetime
    
    console = Console()
    manager = ScheduleManager()
    
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]Error:[/red] Schedule with ID {schedule_id} not found.")
        return
    
    # Get parameters from schedule
    params = schedule.params or {}
    topic = params.get('topic')
    
    # Use the simplified task
    try:
        from celery_queue.simplified_tasks import generate_tweet_task
        task = generate_tweet_task.delay(topic=topic)
        console.print(f"[green]Task started![/green] Task ID: {task.id}")
        
        # Update the schedule record
        manager.update_schedule(schedule_id, 
            is_running=True,
            last_run=datetime.datetime.now(),
            task_id=task.id
        )
        
        return True
    except Exception as e:
        console.print(f"[red]Error starting task:[/red] {str(e)}")
        return False


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
    
    table.add_row("start_daemon", "start", "Start the scheduler daemon")
    table.add_row("stop_daemon", "stop", "Stop the scheduler daemon")
    table.add_row("daemon_status", "status", "Check scheduler status")
    table.add_row("list", "list", "List scheduled tasks")
    table.add_row("set", "create", "Create/update a schedule")
    table.add_row("toggle --enable", "enable", "Enable a schedule")
    table.add_row("toggle --disable", "disable", "Disable a schedule")
    table.add_row("delete", "delete", "Delete a schedule")
    table.add_row("run", "run", "Manually run a task")
    
    console.print(table)
    console.print("\n[bold yellow]Note:[/bold yellow] You can use either command set based on your preference.")


@scheduler.command()
@click.argument('schedule_id', type=int)
def enable(schedule_id):
    """
    Enable a specific schedule.
    
    This is a convenience wrapper around the toggle command.
    """
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
    
    # Enable the schedule
    result = manager.update_schedule(schedule_id, enabled=True)
    
    if result:
        console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) has been enabled.[/green]")
        
        # If enabling, trigger an immediate check
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
    """
    Disable a specific schedule.
    
    This is a convenience wrapper around the toggle command.
    """
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
    
    # Disable the schedule
    result = manager.update_schedule(schedule_id, enabled=False)
    
    if result:
        console.print(f"[green]Schedule '{schedule.name}' (ID: {schedule_id}) has been disabled.[/green]")
        
        # If the schedule was running, stop it
        if schedule.is_running:
            manager.stop_task(schedule_id)
            console.print(f"[yellow]Stopped running task for schedule '{schedule.name}'.[/yellow]")
    else:
        console.print(f"[red]Failed to disable schedule '{schedule.name}' (ID: {schedule_id}).[/red]")


# Add the scheduler group to the main CLI
main.add_command(scheduler)

if __name__ == "__main__":
    main()
