import pytest
from click.testing import CliRunner
from puti.cli import main
from puti.core.config_setup import ensure_twikit_config_is_present

@pytest.mark.real_api
def test_ethan_cli_debuggable_conversation():
    """
    Tests the ethan-chat CLI in a way that allows debugging.

    This test invokes the CLI command directly within the test process,
    allowing you to set breakpoints in the CLI or agent code and step through it.
    It simulates a multi-turn conversation by feeding input to the command.

    Make sure TWIKIT_COOKIE_PATH is set correctly before running.

    To run this test:
        pytest test/puti/test_ehan_cli.py -v

    To debug this test in VSCode, set a breakpoint and run the test using
    the "Python: Debug Tests" command.
    """
    # Ensure Twitter configuration is present
    ensure_twikit_config_is_present()

    runner = CliRunner()

    # The conversation turns, ending with 'exit' to terminate the chat loop
    conversation = [
        "What can you help me with regarding Twitter?",
        "Can you show me my recent Twitter mentions?",
        "What's my Twitter username and how many followers do I have?",
        "Can you draft a tweet about AI that would be interesting to my followers?",
        "exit"
    ]

    # Join the inputs with newlines to simulate the user pressing Enter after each line
    inputs = "\\n".join(conversation) + "\\n"

    # Invoke the command, passing the scripted inputs.
    # The `ethan_chat` function will now be called in this process.
    result = runner.invoke(main, ['ethan-chat'], input=inputs, catch_exceptions=False)

    # --- Assertions ---

    # 1. The CLI should exit gracefully
    assert result.exit_code == 0, f"CLI exited with an error: {result.exception}"

    # 2. Check for key parts of the output
    assert "Chat with Ethan" in result.output
    assert "Chat session ended. Goodbye!" in result.output

    # 3. Verify that the conversation took place
    #    We expect one "You:" prompt for each item in the conversation.
    #    We expect one "Ethan:" response for each item except the final 'exit'.
    assert result.output.count("👤 You:") == len(conversation)
    assert result.output.count("🤖 Ethan") == len(conversation) - 1

    print("\\n\\n===== CLI Debuggable Conversation Test Completed Successfully =====")
    print("The test successfully simulated a user conversation in-process.") 