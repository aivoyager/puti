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
