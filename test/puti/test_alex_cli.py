import pytest
from click.testing import CliRunner
from puti.cli import alex_chat, main
from unittest.mock import AsyncMock


@pytest.fixture
def runner():
    return CliRunner()


def test_alex_chat_exit(runner, monkeypatch):
    # Simulate user typing 'exit'
    monkeypatch.setattr('click.prompt', lambda text: 'exit')

    result = runner.invoke(main, ['alex-chat'])

    assert result.exit_code == 0
    assert "Starting interactive chat with Alex agent. Type 'exit' to quit." in result.output
    assert "You:" in result.output


@pytest.mark.asyncio
async def test_alex_chat_interaction(runner, monkeypatch):
    mock_alex_run = AsyncMock(side_effect=["Hello there!", "I am doing well, thank you!"])
    monkeypatch.setattr('puti.llm.roles.agents.Alex.run', mock_alex_run)

    inputs = ['hello', 'how are you?', 'exit']
    input_iter = iter(inputs)
    monkeypatch.setattr('click.prompt', lambda text: next(input_iter))

    result = runner.invoke(main, ['alex-chat'])

    assert result.exit_code == 0
    assert "Starting interactive chat with Alex agent. Type 'exit' to quit." in result.output
    assert "You:" in result.output
    assert "Alex: Hello there!" in result.output
    assert "Alex: I am doing well, thank you!" in result.output
    assert mock_alex_run.call_count == 2  # Called for 'hello' and 'how are you?'
