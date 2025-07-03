"""
@Author: obstacles
@Time: 2024-08-10
@Description: Tests for the context-aware reply functionality
"""
import pytest
import asyncio
import logging
import os

from puti.llm.roles.agents import Ethan
from puti.llm.actions.x_bot import ContextAwareReplyAction, ContextAwareReplyToMentionsAction

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
lgr = logging.getLogger("test_context_aware_reply")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_aware_reply_integration():
    """
    Tests the ContextAwareReplyAction with the real Twitter API.
    
    This test first asks Ethan to find an unreplied mention, then replies to it.
    This makes the test more dynamic and self-contained.
    
    To run this test:
       pytest test/x_bot/test_context_aware_reply.py::test_context_aware_reply_integration -v -s
    """
    # Create Ethan instance with Twitter capabilities
    ethan = Ethan()

    # Ask Ethan to find a recent unreplied tweet and return its ID
    lgr.info("Asking Ethan to find an unreplied mention...")
    find_tweet_prompt = "Find a recent tweet mentioning me that I haven't replied to yet from the last 24 hours. Just return the tweet ID, and nothing else."

    tweet_id_response = await ethan.run(find_tweet_prompt)

    # Extract the tweet ID from the response (it should be a number)
    import re
    match = re.search(r'\d{18,}', str(tweet_id_response))

    if not match:
        pytest.skip(f"Could not find an unreplied tweet ID to test with. Ethan's response: {tweet_id_response}")

    tweet_id = match.group(0)
    lgr.info(f"Found tweet ID to reply to: {tweet_id}")

    # Configure action with the tweet ID
    action = ContextAwareReplyAction(tweet_id=tweet_id)

    # Run the action
    result = await action.run(ethan)

    # Verify result
    lgr.info(f"Integration test result: {result}")
    assert "error" not in str(result).lower()

    # Print the result for manual verification
    print(f"\nContext-aware reply sent successfully. Result: {result}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_aware_reply_to_mentions_integration():
    """
    Tests the ContextAwareReplyToMentionsAction with the real Twitter API.
    
    This test will find and reply to real mentions. Use with caution.
    
    To run this test:
       pytest test/x_bot/test_context_aware_reply.py::test_context_aware_reply_to_mentions_integration -v -s
    """
    # Create Ethan instance with Twitter capabilities
    ethan = Ethan()

    # Configure action to look for mentions in the last hour
    action = ContextAwareReplyToMentionsAction(
        time_value=1,
        time_unit="hours",
        max_mentions=2
    )

    # Run the action
    result = await action.run(ethan)

    # Verify result
    lgr.info(f"Mentions reply integration test result: {result}")
    assert "error" not in str(result).lower()

    # Print the result for manual verification
    print(f"\nContext-aware reply to mentions finished. Result: {result}")
