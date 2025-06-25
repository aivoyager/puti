import datetime
import puti.bootstrap  # noqa: F401, must be the first import
import click
import asyncio
import questionary
import os
import subprocess

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from puti.db.schedule_manager import ScheduleManager
from puti.llm.roles.agents import Alex, Ethan
from puti.core.config_setup import ensure_twikit_config_is_present
from puti.scheduler import WorkerDaemon, BeatDaemon, ensure_worker_running, ensure_beat_running

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
    
    ctx.obj = {'manager': ScheduleManager()}


@scheduler.command('list')
def list_tasks():
    """Lists all non-deleted tasks."""
    console = Console()
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
            task.task_type,
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
    console = Console()
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
    console = Console()
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
    console = Console()
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
    console = Console()
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
@click.argument('service', type=click.Choice(['worker', 'beat']))
@click.option('--lines', '-n', default=20, help="Number of log lines to show.")
def show_logs(service, lines):
    """Shows logs for the worker or beat service."""
    console = Console()
    daemon = WorkerDaemon() if service == 'worker' else BeatDaemon()
    log_file = daemon.log_file
    
    if not os.path.exists(log_file):
        console.print(f"[red]Log file not found at: {log_file}[/red]")
        return
        
    console.print(Panel(f"Showing last {lines} lines from [bold]{log_file}[/bold]", border_style="blue"))
    try:
        # Use tail for efficiency
        result = subprocess.run(['tail', '-n', str(lines), log_file], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]Error reading log file: {result.stderr}[/red]")
    except FileNotFoundError:
        console.print("[red]Error: 'tail' command not found. Reading file directly.[/red]")
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
            for line in log_lines[-lines:]:
                console.print(line.strip())


if __name__ == '__main__':
    main()
