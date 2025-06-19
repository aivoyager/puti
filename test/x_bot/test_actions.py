"""
@Author: obstacles
@Time:  2025-06-20 10:00
@Description:  Tests for the x_bot actions.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from puti.llm.actions.x_bot import GenerateTweetAction, PublishTweetAction
from puti.llm.messages import AssistantMessage


@pytest.mark.asyncio
async def test_generate_tweet_action():
    """
    Tests the GenerateTweetAction to ensure it follows the three-step process:
    1. Generate a topic.
    2. Generate a tweet based on the topic.
    3. Review the tweet.
    """
    # Mock the OpenAINode's chat method to return predefined responses
    mock_chat = AsyncMock(side_effect=[
        AssistantMessage(content="AI in software development"),  # Mocked topic
        AssistantMessage(content="AI is transforming software development by automating tasks..."),  # Mocked tweet
        AssistantMessage(content="Reviewed: AI is transforming software development...")  # Mocked review
    ])

    with patch('puti.llm.actions.x_bot.OpenAINode') as MockOpenAINode:
        # Configure the mock instance to use our mock_chat
        mock_instance = MockOpenAINode.return_value
        mock_instance.chat = mock_chat

        # Create an instance of the action
        action = GenerateTweetAction()

        # Run the action (the 'role' argument is now ignored by run)
        result = await action.run()

        # Assertions
        assert mock_chat.call_count == 3

        # Check the final result
        assert "Reviewed" in result.content

        # Verify the prompts sent to the LLM
        # 1. Topic generation
        topic_call_args = mock_chat.call_args_list[0].args[0]
        assert "Generate a trending topic" in topic_call_args[0]['content']

        # 2. Tweet generation
        tweet_gen_call_args = mock_chat.call_args_list[1].args[0]
        assert "AI in software development" in tweet_gen_call_args[0]['content']

        # 3. Tweet review
        review_call_args = mock_chat.call_args_list[2].args[0]
        assert "AI is transforming software development" in review_call_args[0]['content']


@pytest.mark.asyncio
async def test_publish_tweet_action():
    """
    Tests the PublishTweetAction to ensure it correctly prepares the prompt for publishing.
    """
    action = PublishTweetAction()

    # Mock the previous result that would be passed to this action
    previous_result = AssistantMessage(content="This is the final tweet to be published.")

    # The 'role' and its 'run' method will be called by the action's 'run'
    mock_role = AsyncMock()
    mock_role.run = AsyncMock(return_value="Tweet successfully posted.")

    # Run the action
    result = await action.run(role=mock_role, previous_result=previous_result)

    # Assertions
    mock_role.run.assert_called_once()

    # Check the prompt sent to the role's run method
    run_args = mock_role.run.call_args.kwargs
    assert "I will now post the following tweet" in run_args['prompt']
    assert "This is the final tweet to be published." in run_args['prompt']

    # Check the final result from the action
    assert result == "Tweet successfully posted."
