import puti.bootstrap  # noqa: F401, must be the first import
import click
import asyncio
from puti.llm.roles.agents import Alex


@click.group()
def main():
    """Puti CLI Tool"""
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
    click.echo(f"Starting interactive chat with {name} agent. Type 'exit' to quit.")
    alex_agent = Alex(name=name)

    async def chat_loop():
        while True:
            user_input = click.prompt("You")
            if user_input.lower() == 'exit':
                click.echo("Exiting chat.")
                break
            try:
                # TODO: true response
                response = await alex_agent.run(user_input)
                click.echo(f"{name}: {response}")
            except Exception as e:
                click.echo(f"Error: {e}")

    asyncio.run(chat_loop())
