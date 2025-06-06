import puti.bootstrap  # noqa: F401, must be the first import
import click
import asyncio
import questionary
from rich.console import Console
from rich.markdown import Markdown
from puti.llm.roles.agents import Alex
from puti.core.config_setup import ensure_config_is_present


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

                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                # Show a thinking indicator
                with console.status("[bold cyan]Alex is thinking...", spinner="dots") as status:
                    response = await alex_agent.run(user_input)
                
                # Print the response as markdown
                response_markdown = Markdown(response, style="green")
                console.print(f"[bold green]{name}:[/bold green]", response_markdown)

            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C and Ctrl+D
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print("\n[bold yellow]Chat session ended. Goodbye![/bold yellow]")
