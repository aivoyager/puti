import click
import asyncio
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from puti.logs import logger_factory


@click.group()
def main():
    """PuTi: Your AI-powered command-line assistant."""
    # Bootstrap the application. DB setup is now handled by the specific
    # managers when they are instantiated, or by test fixtures.
    import puti.bootstrap


@main.command(name='alex-chat')
@click.option('--name', default='Alex', help='Name of the Alex agent.')
def alex_chat(name):
    """Starts an interactive chat session with the Alex agent."""
    from puti.llm.roles.agents import Alex
    console = Console()
    console.print(Panel(
        f"[bold green]Welcome to the chat with {name}![/bold green]",
        title="Welcome",
        border_style="cyan"
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
""")
    console.print(welcome_message)

    alex_agent = Alex(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await asyncio.to_thread(console.input, "[bold blue]You: [/bold blue]")
                if user_input.lower() in ["exit", "quit"]:
                    break

                console.print(Panel(user_input, title="👤 You", border_style="blue"))

                with console.status(f"[bold cyan]{name} is thinking...", spinner="dots"):
                    response = await alex_agent.run(user_input)

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


@main.command()
@click.option('--name', default='Ethan', help='Name of the Ethan agent.')
def ethan_chat(name):
    """Starts an interactive chat session with the Ethan agent."""
    from puti.llm.roles.agents import Ethan
    from puti.core.config_setup import ensure_twikit_config_is_present
    console = Console()

    # Ensure Twikit config is present before starting
    ensure_twikit_config_is_present()

    console.print(Panel(
        f"[bold green]Welcome to the chat with {name}![/bold green]",
        title="Welcome",
        border_style="cyan"
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
""")
    console.print(welcome_message)

    ethan_agent = Ethan(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await asyncio.to_thread(console.input, "[bold blue]You: [/bold blue]")
                if user_input.lower() in ["exit", "quit"]:
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
    """Manage the tweet scheduler daemon."""
    pass


@scheduler.command()
def start():
    """Starts the tweet scheduler daemon."""
    from puti.scheduler import SchedulerDaemon
    lgr = logger_factory.default
    lgr.info("Starting the tweet scheduler daemon...")
    daemon = SchedulerDaemon()
    daemon.start()


@scheduler.command()
@click.option('--schedule', '-s', required=True, help='Cron-style schedule string (e.g., "0 * * * *").')
@click.option('--topic', '-t', default=None, help='A specific topic for the tweet generation.')
def set(schedule, topic):
    """Creates or updates the schedule for the CLI-managed tweet task."""
    from puti.db.schedule_manager import ScheduleManager
    from puti.db.model.task.bot_task import TweetSchedule
    lgr = logger_factory.default
    lgr.info("Setting the tweet schedule...")

    schedule_manager = ScheduleManager(model_type=TweetSchedule)
    schedule_name = 'cli_managed_schedule'

    existing_schedule = schedule_manager.get_by_name(schedule_name)

    if existing_schedule:
        updates = {
            "cron_schedule": schedule,
            "enabled": True,
            "task_parameters": {"topic": topic}
        }
        schedule_manager.update(existing_schedule.id, updates)
        lgr.info(f"Updated existing schedule '{schedule_name}'.")
        click.echo(f"Updated schedule '{schedule_name}'.")
    else:
        new_schedule = TweetSchedule(
            name=schedule_name,
            cron_schedule=schedule,
            enabled=True,
            task_parameters={"topic": topic}
        )
        schedule_manager.save(new_schedule)
        lgr.info(f"Created new schedule '{schedule_name}'.")
        click.echo(f"Created new schedule '{schedule_name}'.")


@scheduler.command()
def stop():
    """Stops the tweet scheduler daemon and disables the schedule."""
    from puti.scheduler import SchedulerDaemon
    from puti.db.schedule_manager import ScheduleManager
    lgr = logger_factory.default
    lgr.info("Stopping the tweet scheduler...")

    daemon = SchedulerDaemon()
    daemon.stop()

    schedule_manager = ScheduleManager(model_type=TweetSchedule)
    schedule_name = 'cli_managed_schedule'
    existing_schedule = schedule_manager.get_by_name(schedule_name)

    if existing_schedule:
        schedule_manager.update(existing_schedule.id, {"enabled": False})
        lgr.info(f"Disabled schedule '{schedule_name}' in the database.")
        click.echo(f"Disabled schedule '{schedule_name}'.")


if __name__ == '__main__':
    main()
