"""
Test context-aware tweet replies with real components.
This test uses real EthanG instances and workflows, with optional mocking.
"""
import os
import sys
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_context_aware_reply")

# Add project root to Python path to ensure correct imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

# Import necessary modules
from puti.db.task_state_guard import TaskStateGuard
from puti.llm.roles.agents import Ethan
from puti.llm.actions.x_bot import ContextAwareReplyAction, ContextAwareReplyToMentionsAction
from puti.llm.tools.twikitt import ToolResponse


class MockTaskStateGuard:
    """
    Mock TaskStateGuard class to avoid database operations
    """
    @classmethod
    @patch.object(TaskStateGuard, '__init__', return_value=None)
    @patch.object(TaskStateGuard, '__enter__', return_value=MagicMock())
    @patch.object(TaskStateGuard, '__exit__', return_value=False)
    @patch.object(TaskStateGuard, 'update_state')
    def mock_for_task(cls, mock_update_state, mock_exit, mock_enter, mock_init, task_id=None, schedule_id=None):
        """Mock the TaskStateGuard.for_task method"""
        mock_guard = MagicMock()
        mock_guard.update_state = mock_update_state
        
        # Log operations instead of performing actual database operations
        def update_state_impl(**kwargs):
            logger.info(f"[MockTaskStateGuard] update_state called with: {kwargs}")
        
        mock_update_state.side_effect = update_state_impl
        
        return mock_guard


async def test_context_aware_reply_task_with_mock():
    """Test context-aware reply to tweets with mock Twikitt tool responses"""
    
    logger.info("Starting context-aware reply task test with mocked responses")
    
    # Replace TaskStateGuard.for_task to avoid database operations
    original_for_task = TaskStateGuard.for_task
    TaskStateGuard.for_task = MockTaskStateGuard.mock_for_task
    
    try:
        # Create mock mentions data as JSON string (as the model would return)
        mock_mentions_json = """```json
        [
            {
                "mention_id": "123456",
                "text": "What's your opinion on AI in healthcare?",
                "author_id": "user1",
                "parent_id": null,
                "data_time": "2023-01-01T12:00:00Z",
                "replied": false
            },
            {
                "mention_id": "234567",
                "text": "Have you seen the latest developments in LLMs?",
                "author_id": "user2",
                "parent_id": null,
                "data_time": "2023-01-01T12:05:00Z",
                "replied": false
            }
        ]
        ```"""
        
        # Create mock thread data for each mention
        mock_thread_data = {
            "123456": {
                "original_tweet": {
                    "id": "123456",
                    "text": "What's your opinion on AI in healthcare?",
                    "user": {
                        "id": "user1",
                        "name": "Healthcare Expert",
                        "screen_name": "health_expert"
                    },
                    "created_at": "2023-01-01T12:00:00Z"
                },
                "parent_tweets": [],
                "current_tweet": {
                    "id": "123456",
                    "text": "What's your opinion on AI in healthcare?",
                    "user": {
                        "id": "user1",
                        "name": "Healthcare Expert",
                        "screen_name": "health_expert"
                    },
                    "created_at": "2023-01-01T12:00:00Z"
                },
                "replies": []
            },
            "234567": {
                "original_tweet": {
                    "id": "234567",
                    "text": "Have you seen the latest developments in LLMs?",
                    "user": {
                        "id": "user2",
                        "name": "AI Researcher",
                        "screen_name": "ai_researcher"
                    },
                    "created_at": "2023-01-01T12:05:00Z"
                },
                "parent_tweets": [],
                "current_tweet": {
                    "id": "234567",
                    "text": "Have you seen the latest developments in LLMs?",
                    "user": {
                        "id": "user2",
                        "name": "AI Researcher",
                        "screen_name": "ai_researcher"
                    },
                    "created_at": "2023-01-01T12:05:00Z"
                },
                "replies": []
            }
        }
        
        # Mock reply data for each mention
        mock_reply_data = {
            "123456": "AI is transforming healthcare through better diagnostics, personalized treatment plans, and improving administrative efficiency. It's an exciting field with great potential to improve patient outcomes.",
            "234567": "Recent LLM developments include improved reasoning, more accurate tool use, and better alignment with human values. The pace of innovation continues to be remarkable!"
        }
        
        # Create an Ethan agent
        ethan = Ethan()
        
        # Patch Ethan's run method to simulate conversation
        original_run = ethan.run
        
        async def mock_run(msg, *args, **kwargs):
            # Check if this is the get_mentions command
            if isinstance(msg, str) and "get_mentions" in msg:
                return mock_mentions_json
                
            # Check if this is a get_conversation_thread command
            elif isinstance(msg, str) and "get_conversation_thread" in msg:
                # Extract tweet ID from message
                tweet_id_match = re.search(r'tweet ID (\d+)', msg)
                if tweet_id_match:
                    tweet_id = tweet_id_match.group(1)
                    if tweet_id in mock_thread_data:
                        return f"```json\n{json.dumps(mock_thread_data[tweet_id])}\n```"
                    else:
                        return f"No thread data found for tweet {tweet_id}"
            
            # Check if this is for generating a reply content
            elif isinstance(msg, str) and ("healthcare" in msg or "AI in healthcare" in msg):
                return mock_reply_data["123456"]
            elif isinstance(msg, str) and ("LLMs" in msg or "latest developments" in msg):
                return mock_reply_data["234567"]
            
            # Check if this is the reply_to_tweet command
            elif isinstance(msg, str) and "reply_to_tweet" in msg:
                tweet_id_match = re.search(r'tweet ID (\d+)', msg)
                if tweet_id_match:
                    tweet_id = tweet_id_match.group(1)
                    logger.info(f"Mock reply to tweet {tweet_id}")
                    return f"Reply sent successfully to tweet {tweet_id}"
            
            # Generic response for other queries
            return "I'll help with that task."
        
        # Apply the mock
        ethan.run = AsyncMock(side_effect=mock_run)
        
        # Create the action
        action = ContextAwareReplyToMentionsAction(
            time_value=1,
            time_unit="days",
            max_context_depth=3,
            max_mentions=2
        )
        
        # Run the action
        result = await action.run(ethan)
        
        # Print the results
        print(f"\nContext-aware reply task results: {result}")
        
        # Assert basic results
        assert "Processed" in result
        assert "123456" in result
        assert "234567" in result
        
        # Verify the correct calls were made
        get_mentions_calls = [call[0][0] for call in ethan.run.call_args_list 
                              if isinstance(call[0][0], str) and "get_mentions" in call[0][0]]
        assert len(get_mentions_calls) == 1
        
        get_thread_calls = [call[0][0] for call in ethan.run.call_args_list 
                            if isinstance(call[0][0], str) and "get_conversation_thread" in call[0][0]]
        assert len(get_thread_calls) == 2
        
        reply_calls = [call[0][0] for call in ethan.run.call_args_list 
                       if isinstance(call[0][0], str) and "reply_to_tweet" in call[0][0]]
        assert len(reply_calls) == 2
        
        return result
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        print(f"\nTest failed: {e}")
        return f"Error: {str(e)}"
        
    finally:
        # Restore original method
        TaskStateGuard.for_task = original_for_task


async def test_context_aware_reply_task_real():
    """Test context-aware reply to tweets with real API calls
    
    Warning: This will make actual API calls and potentially send real tweets.
    Only run this test in a controlled environment with test accounts.
    """
    logger.info("Starting context-aware reply task test with REAL API calls")
    print("\n⚠️  WARNING: This test makes REAL API calls and may post actual tweets!")
    
    # Ask for confirmation
    response = input("Are you sure you want to continue? (y/n): ")
    if response.lower() != 'y':
        print("Test aborted.")
        return "Test aborted by user"
    
    # Replace TaskStateGuard.for_task to avoid database operations
    original_for_task = TaskStateGuard.for_task
    TaskStateGuard.for_task = MockTaskStateGuard.mock_for_task
    
    try:
        from puti.core.config_setup import ensure_twikit_config_is_present
        
        # Ensure Twitter configuration is present
        ensure_twikit_config_is_present()
        
        # Create an Ethan agent
        ethan = Ethan()
        
        # Create the action with limited scope (1 hour, max 1 mention)
        # to minimize real-world impact
        action = ContextAwareReplyToMentionsAction(
            time_value=1,
            time_unit="hours",
            max_context_depth=3,
            max_mentions=1
        )
        
        # Run the action with real API calls
        result = await action.run(ethan)
        
        # Print the results
        print(f"\nReal API context-aware reply task results: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error during real API test: {e}", exc_info=True)
        print(f"\nReal API test failed: {e}")
        return f"Error: {str(e)}"
        
    finally:
        # Restore original method
        TaskStateGuard.for_task = original_for_task


if __name__ == "__main__":
    # Parse command line arguments to determine which test to run
    import argparse
    
    parser = argparse.ArgumentParser(description="Test context-aware tweet replies")
    parser.add_argument("--real-api", action="store_true", help="Run test with real API calls (use with caution!)")
    args = parser.parse_args()
    
    if args.real_api:
        asyncio.run(test_context_aware_reply_task_real())
    else:
        asyncio.run(test_context_aware_reply_task_with_mock()) 