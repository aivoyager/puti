import pytest
import os
from unittest.mock import AsyncMock
from dotenv import load_dotenv
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from celery_queue.simplified_tasks import reply_to_tweets_task

from puti.llm.tools.twikitt import Twikitt, TwikittClientManager


# Mock tweet object structure for tests
class MockUser:
    def __init__(self, name, user_id=None, followers_count=0, following_count=0, description=""):
        self.name = name
        self.id = user_id or name
        self.screen_name = name
        self.followers_count = followers_count
        self.following_count = following_count
        self.description = description


class MockTweet:
    def __init__(self, id, text, user, created_at="2023-01-01T12:00:00.000Z"):
        self.id = id
        self.text = text
        self.user = user
        self.created_at = created_at


class MockNotification:
    def __init__(self, id, tweet, from_user):
        self.id = id
        self.tweet = tweet
        self.from_user = from_user


@pytest.fixture
def twikit_tool():
    """Fixture to provide a Twikitt instance for tests."""
    return Twikitt()


@pytest.mark.asyncio
async def test_twikit_send_tweet(twikit_tool, monkeypatch):
    """Test sending a tweet."""
    mock_client = AsyncMock()
    mock_user = MockUser(name="test_user", user_id="test_user_id")
    mock_client.create_tweet.return_value = MockTweet(id="12345", text="Test tweet content", user=mock_user)

    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('send_tweet', text='Test tweet content')

    assert response.is_success()
    assert "Tweet sent successfully: 12345" in response.data
    mock_client.create_tweet.assert_called_once_with(text='Test tweet content')


@pytest.mark.asyncio
async def test_twikit_reply_to_tweet(twikit_tool, monkeypatch):
    """Test replying to a tweet."""
    mock_client = AsyncMock()
    mock_user = MockUser(name="test_user", user_id="test_user_id")
    mock_client.create_tweet.return_value = MockTweet(id="67890", text="Test reply content", user=mock_user)

    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('reply_to_tweet', text='Test reply content', tweet_id='12345')

    assert response.is_success()
    assert "Reply sent successfully to tweet 12345: 67890" in response.data
    mock_client.create_tweet.assert_called_once_with(text='Test reply content', reply_to='12345')


@pytest.mark.asyncio
async def test_twikit_browse_tweets(twikit_tool, monkeypatch):
    """Test browsing tweets."""
    mock_client = AsyncMock()
    mock_user1 = MockUser(name="user1", user_id="user1_id")
    mock_user2 = MockUser(name="user2", user_id="user2_id")
    mock_tweets = [
        MockTweet(id="1", text="First tweet", user=mock_user1),
        MockTweet(id="2", text="Second tweet", user=mock_user2)
    ]
    mock_client.search_tweet.return_value = mock_tweets

    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('browse_tweets', query='test query')

    assert response.is_success()
    expected_data = [
        {'id': '1', 'text': 'First tweet', 'user': 'user1'},
        {'id': '2', 'text': 'Second tweet', 'user': 'user2'}
    ]
    assert response.data == expected_data
    mock_client.search_tweet.assert_called_once_with(query='test query', product='Latest')


@pytest.mark.asyncio
async def test_twikit_get_mentions(twikit_tool, monkeypatch):
    """Test getting mentions."""
    mock_client = AsyncMock()
    from_user = MockUser(name="mentioner", user_id="user123")
    tweet_user = MockUser(name="mentioner", user_id="user123")
    mention_tweet = MockTweet(id="tweet1", text="Hello @me", user=tweet_user)

    mock_notifications = [
        MockNotification(
            id="notif1",
            tweet=mention_tweet,
            from_user=from_user
        )
    ]
    mock_client.get_notifications.return_value = mock_notifications

    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('get_mentions')

    assert response.is_success()
    expected_data = [{
        'notification_id': 'notif1',
        'tweet_id': 'tweet1',
        'text': 'Hello @me',
        'from_user_id': 'user123',
        'from_user_name': 'mentioner'
    }]
    assert response.data == expected_data
    mock_client.get_notifications.assert_called_once_with(type='Mentions')


@pytest.mark.asyncio
async def test_twikit_get_my_info(twikit_tool, monkeypatch):
    """Test getting my user info."""
    mock_client = AsyncMock()
    mock_user = MockUser(
        name="Test User",
        user_id="testuser123",
        followers_count=100,
        following_count=50,
        description="A test user."
    )
    mock_client.user.return_value = mock_user

    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('get_my_info')

    assert response.is_success()
    expected_data = {
        'id': 'testuser123',
        'name': 'Test User',
        'screen_name': 'Test User',
        'followers_count': 100,
        'following_count': 50,
        'description': 'A test user.'
    }
    assert response.data == expected_data
    mock_client.user.assert_called_once()


@pytest.mark.asyncio
async def test_twikit_get_my_tweets(twikit_tool, monkeypatch):
    """Test getting my own tweets."""
    mock_client = AsyncMock()

    mock_me = MockUser(name="Test User", user_id="testuser123")
    mock_client.user.return_value = mock_me

    mock_user_tweets = [
        MockTweet(id="t1", text="My first tweet", user=mock_me, created_at="2023-01-01T12:00:00.000Z"),
        MockTweet(id="t2", text="My second tweet", user=mock_me, created_at="2023-01-02T12:00:00.000Z")
    ]
    mock_client.get_user_tweets.return_value = mock_user_tweets

    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('get_my_tweets', count=5)

    assert response.is_success()
    expected_data = [
        {'id': 't1', 'text': 'My first tweet', 'created_at': '2023-01-01T12:00:00.000Z'},
        {'id': 't2', 'text': 'My second tweet', 'created_at': '2023-01-02T12:00:00.000Z'}
    ]
    assert response.data == expected_data

    mock_client.user.assert_called_once()
    mock_client.get_user_tweets.assert_called_once_with('testuser123', 'Tweets', count=5)


@pytest.mark.asyncio
async def test_twikit_like_tweet(twikit_tool, monkeypatch):
    """Test liking a tweet."""
    mock_client = AsyncMock()
    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('like_tweet', tweet_id='tweet123')

    assert response.is_success()
    assert response.data == "Tweet tweet123 liked successfully."
    mock_client.favorite_tweet.assert_called_once_with('tweet123')


@pytest.mark.asyncio
async def test_twikit_retweet(twikit_tool, monkeypatch):
    """Test retweeting a tweet."""
    mock_client = AsyncMock()
    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))

    response = await twikit_tool.run('retweet', tweet_id='tweet456')

    assert response.is_success()
    assert response.data == "Tweet tweet456 retweeted successfully."
    mock_client.retweet.assert_called_once_with('tweet456')


@pytest.mark.integration
@pytest.mark.asyncio
async def test_twikit_real_send_tweet():
    """
    Integration test to send a real tweet.
    This test requires a .env file with TWIKIT_COOKIE_PATH set.
    """
    load_dotenv()

    if not os.getenv("TWIKIT_COOKIE_PATH"):
        pytest.skip("Skipping integration test: TWIKIT_COOKIE_PATH not set in .env file.")

    tool = Twikitt()
    # To ensure a fresh client is created for this test if mocks were used before
    tool.client_manager._client = None
    
    import time
    tweet_content = f"This is a test tweet from the integration test at {time.time()}."
    response = await tool.run('send_tweet', text=tweet_content)

    assert response.is_success()
    assert "Tweet sent successfully:" in response.data


@pytest.mark.asyncio
async def test_twikit_missing_cookie_path(monkeypatch):
    """Test tool failure when cookie path is not set."""
    if "TWIKIT_COOKIE_PATH" in os.environ:
        monkeypatch.delenv("TWIKIT_COOKIE_PATH")

    # We need a new instance to re-evaluate the env var because of the singleton pattern
    client_manager = TwikittClientManager()
    # Reset internal state for the test to ensure get_client re-runs initialization
    client_manager._client = None

    tool = Twikitt()
    tool.client_manager = client_manager

    response = await tool.run('send_tweet', text='This should fail')

    assert not response.is_success()
    assert "TWIKIT_COOKIE_PATH environment variable not set or file not found" in response.msg


@pytest.mark.asyncio
async def test_twikit_unknown_command(twikit_tool, monkeypatch):
    """Test handling of an unknown command."""
    # Mock the client to prevent actual login attempts
    mock_client = AsyncMock()
    monkeypatch.setattr(twikit_tool.client_manager, 'get_client', AsyncMock(return_value=mock_client))
    
    response = await twikit_tool.run('non_existent_command')
    assert not response.is_success()
    assert "Unknown command: non_existent_command" in response.msg 