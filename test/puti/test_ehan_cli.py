import pytest
from click.testing import CliRunner
from puti.cli import main
from unittest.mock import AsyncMock


@pytest.fixture
def runner():
    return CliRunner()


def test_ehan_chat_exit(runner, monkeypatch):
    # Simulate user typing 'exit'
    mock_question = AsyncMock()
    mock_question.ask_async.return_value = 'exit'
    monkeypatch.setattr('questionary.text', lambda message, qmark: mock_question)

    result = runner.invoke(main, ['ethan-chat'])

    assert result.exit_code == 0
    assert "Chat with Ethan" in result.output


@pytest.mark.asyncio
async def test_ehan_chat_interaction(runner, monkeypatch):
    inputs = ['hello', 'how are you?', 'exit']
    input_iter = iter(inputs)

    # Create an async mock that returns values from the iterator
    async def mock_ask_async():
        return next(input_iter)

    mock_question = AsyncMock()
    mock_question.ask_async.side_effect = mock_ask_async
    monkeypatch.setattr('questionary.text', lambda message, qmark: mock_question)

    result = runner.invoke(main, ['ethan-chat'])

    assert result.exit_code == 0
    assert "Chat with Ethan" in result.output
    assert result.output.count("👤 You:") >= 1 