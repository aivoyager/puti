import json
import puti.bootstrap  # noqa: F401, must be the first import
import click
import asyncio
import questionary
from rich.console import Console
import multiprocessing
import sys
import logging
from rich.markdown import Markdown
from puti.llm.roles.agents import Alex
from puti.core.config_setup import ensure_config_is_present

# --- Aggressive fix for stubborn logs and warnings on macOS ---

# 1. Globally suppress INFO and DEBUG logs.
# This configures the root logger. Any library (like mcp) that tries to
# configure logging after this will find it already configured, and its
# settings for lower-level logs will be ignored.
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


# 2. Disable the resource_tracker to silence semaphore leak warnings.
# This is a last-resort hack for when warnings persist despite all other fixes.
# It prevents the tracker from ever registering resources, so it never warns.
if sys.platform == 'darwin':
    from multiprocessing import resource_tracker
    def _noop(*args, **kwargs):
        pass
    resource_tracker.register = _noop
    resource_tracker.unregister = _noop
    
    # We still set the start method to 'fork' as it's more efficient for this app.
    try:
        multiprocessing.set_start_method('fork')
    except RuntimeError:
        # Guards against "context has already been set" errors.
        pass


@click.group()
def main():
    """Puti CLI Tool: An interactive AI assistant."""
    ensure_config_is_present()
    pass


@main.command()
@click.option('--name', default='Puti', help='Name to greet.')
def hello(name):
    """Greets the user."""
    click.echo(f"Hello, {name}!")


@main.command()
@click.option('--name', default='Alex', help='Name of the Alex agent.')
def alex_chat(name):
    """Starts an interactive chat with Alex agent using questionary."""
    console = Console()
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
                user_input = await questionary.text("You:").ask_async()
                # user_input = '你好呀'

                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                # Show a thinking indicator
                with console.status("[bold cyan]Alex is thinking...", spinner="dots"):
                    user_input += '\n [System: Reply in the specified json format.]'
                    response = await alex_agent.run(user_input)
                
                # The agent returns a dictionary. We extract the final answer for the user.
                final_answer = "Sorry, I encountered an issue and couldn't provide a response."

                # Print the response as markdown, with a newline for spacing.
                response_markdown = Markdown(response, style="green")
                console.print(f"\n[bold blue]{name}:[/bold blue]", response_markdown)

            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C and Ctrl+D
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print("\n[bold yellow]Chat session ended. Goodbye![/bold yellow]")
