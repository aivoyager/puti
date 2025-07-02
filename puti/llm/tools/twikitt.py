import asyncio
import os
from abc import ABC
from typing import Literal, Optional, Type, Union, List

from httpx import ConnectTimeout
from pydantic import Field, ConfigDict
from twikit import Client, Tweet
from twikit.utils import Result
import pytz
import re
import datetime

from puti.core.resp import ToolResponse
from puti.llm.tools import BaseTool, ToolArgs
from puti.logs import logger_factory

lgr = logger_factory.llm


class TwikittClientManager:
    _instance = None
    _client = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TwikittClientManager, cls).__new__(cls)
        return cls._instance

    async def login(self):
        """
        Logs in the client if not already logged in. Then, verifies the
        connection by fetching user info, and retries on failure.
        """
        async with self._lock:
            # Step 1: One-time login if client does not exist
            if self._client is None:
                # lgr.info("No active Twikit client. Performing initial login.")
                cookie_path = os.getenv("TWIKIT_COOKIE_PATH")
                if not cookie_path or not os.path.exists(cookie_path):
                    raise ValueError("TWIKIT_COOKIE_PATH environment variable not set or file not found.")

                client = Client()
                client.load_cookies(cookie_path)
                self._client = client
                # lgr.info("Twikit client initialized.")

            # Step 2: Verify session by fetching user info, with retries.
            max_retries = 3
            last_exception = None
            for attempt in range(max_retries):
                try:
                    user_info = await self._client.user()
                    # lgr.info(
                    #     f"Twikit login successful. Logged in as: "
                    #     f"{user_info.name} (@{user_info.screen_name})"
                    # )
                    return  # Success
                except Exception as e:
                    last_exception = e
                    lgr.error(f"Verification attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)

            # If loop finishes, all retries have failed.
            self._client = None  # Invalidate the client for the next run.
            raise Exception(
                "Failed to verify session after 3 attempts. "
                f"Your cookie may be expired. Last error: {last_exception}"
            )

    async def get_client(self) -> Client:
        if self._client is None:
            # This should ideally be called by a login method first
            raise RuntimeError("Client not initialized. Please call login() first.")
        return self._client


class TwikittArgs(ToolArgs, ABC):
    command: Literal[
        'send_tweet', 'reply_to_tweet', 'browse_tweets', 'get_mentions', 'get_my_info',
        'get_my_tweets', 'like_tweet', 'retweet', 'get_user_name_by_id', 'has_my_reply',
        'check_reply_status_batch', 'get_tweet_replies'
    ] = Field(
        ...,
        description='The command to run. Can be "send_tweet", "reply_to_tweet", "get_mentions", "has_my_reply", "check_reply_status_batch", "get_tweet_replies", etc.'
    )
    text: Optional[str] = Field(None, description='The text content for a tweet or reply.')
    tweet_id: Optional[str] = Field(None, description='The ID of a specific tweet for operations like replying, liking, retweeting, checking for a reply, or fetching replies.')
    tweet_ids: Optional[List[str]] = Field(None, description='A list of tweet IDs to check reply status for in a batch.')
    user_id: Optional[str] = Field(None, description='The ID of a user for lookup operations.')
    query: Optional[str] = Field(None, description='The keyword or content to search for tweets.')
    count: Optional[int] = Field(default=20, description='The number of items to retrieve. For reply checks, this is the number of your recent tweets to scan to find a reply.')
    start_time: Optional[str] = Field(None, description='The start time for fetching mentions, in ISO 8601 format (e.g., "2023-01-01T12:00:00Z"). Used with "get_mentions".')
    cursor: Optional[str] = Field(None, description='A pagination cursor to retrieve the next set of results for commands like "get_tweet_replies".')


class Twikitt(BaseTool, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    name: str = "twikitt"
    desc: str = (
        "A real-time tool for interacting with Twitter using twikit. "
        "It can send tweets, reply, check reply status, and browse tweets. "
        "It operates directly with the Twitter API without a local database."
    )
    args: TwikittArgs = None

    client_manager: TwikittClientManager = TwikittClientManager()

    async def login(self) -> Optional[ToolResponse]:
        """
        Ensures the client is logged in before performing any action.
        Returns a ToolResponse on failure, None on success.
        """
        try:
            await self.client_manager.login()
            return None
        except Exception as e:
            return ToolResponse.fail(str(e))

    async def _check_my_replies_to_tweets(
        self, client: Client, tweet_ids_to_check: List[str], my_tweets_count: int
    ) -> set:
        """Checks which of the given tweet IDs have been replied to by the current user by fetching their latest tweets."""
        me = await client.user()
        my_tweets = await client.get_user_tweets(me.id, 'Tweets', count=my_tweets_count)

        # Get the set of tweet IDs that the user has replied to
        replied_to_parent_ids = {
            tweet.in_reply_to for tweet in my_tweets if tweet.in_reply_to
        }

        # Find the intersection
        found_replied_ids = set(tweet_ids_to_check) & replied_to_parent_ids
        return found_replied_ids

    async def run(self, *args, **kwargs) -> ToolResponse:
        lgr.debug(f'{self.name} using...')
        login_response = await self.login()
        if login_response:
            return login_response

        try:
            client = await self.client_manager.get_client()
        except Exception as e:
            return ToolResponse.fail(str(e))

        command = kwargs.get('command')
        if not command:
            return ToolResponse.fail("`command` is a required argument.")

        if command == 'send_tweet':
            text = kwargs.get('text')
            if not text:
                return ToolResponse.fail("`text` is required for send_tweet.")
            try:
                tweet = await client.create_tweet(text=text)
                return ToolResponse.success(f"Tweet sent successfully: {tweet.id}")
            except Exception as e:
                return ToolResponse.fail(f"Failed to send tweet: {e}")

        elif command == 'reply_to_tweet':
            text = kwargs.get('text')
            tweet_id = kwargs.get('tweet_id')
            if not text or not tweet_id:
                return ToolResponse.fail("`text` and `tweet_id` are required for reply_to_tweet.")

            try:
                # Real-time check to see if already replied
                count = kwargs.get('count', 200)
                found_replies = await self._check_my_replies_to_tweets(client, [tweet_id], count)
                if found_replies:
                    return ToolResponse.success(f"You have already replied to tweet {tweet_id}.")

                reply_tweet = await client.create_tweet(text=text, reply_to=tweet_id)
                return ToolResponse.success(f"Reply sent successfully to tweet {tweet_id}: {reply_tweet.id}")
            except Exception as e:
                return ToolResponse.fail(f"Failed to reply to tweet: {e}")

        elif command == 'get_mentions':
            try:
                user_info = await client.user()
                query = f'@{user_info.screen_name}'
                count = kwargs.get('count', 20)
                
                tweets = await client.search_tweet(query=query, product='Latest', count=count)
                
                mentions_data = [{
                    'id': t.id,
                    'text': t.text,
                    'user': {'id': t.user.id, 'name': t.user.name, 'screen_name': t.user.screen_name},
                    'created_at': t.created_at
                } for t in tweets]
                
                return ToolResponse.success(mentions_data)
            except Exception as e:
                lgr.error(f"Failed to get mentions: {e}", exc_info=True)
                return ToolResponse.fail(f"Failed to get mentions: {e}")

        elif command == 'get_my_tweets':
            try:
                count = kwargs.get('count', 20)
                me = await client.user()
                my_tweets = await client.get_user_tweets(me.id, 'Tweets', count=count)
                tweet_data = [{
                    'id': t.id, 
                    'text': t.text, 
                    'created_at': t.created_at,
                    'user': {'id': me.id, 'name': me.name, 'screen_name': me.screen_name}
                } for t in my_tweets]
                return ToolResponse.success(tweet_data)
            except Exception as e:
                return ToolResponse.fail(f"Failed to get my tweets: {e}")

        elif command == 'has_my_reply':
            tweet_id = kwargs.get('tweet_id')
            if not tweet_id:
                return ToolResponse.fail("`tweet_id` is required for has_my_reply.")
            
            try:
                count = kwargs.get('count', 200)
                found_replies = await self._check_my_replies_to_tweets(client, [tweet_id], count)
                return ToolResponse.success({
                    'tweet_id': tweet_id,
                    'has_my_reply': bool(found_replies)
                })
            except Exception as e:
                return ToolResponse.fail(f"Failed to check reply status for tweet {tweet_id}: {e}")

        elif command == 'check_reply_status_batch':  # TODO: All unreplied tweet fix
            tweet_ids = kwargs.get('tweet_ids')
            if not tweet_ids:
                return ToolResponse.fail("`tweet_ids` list is required.")

            try:
                count = kwargs.get('count', 200)
                found_replies_set = await self._check_my_replies_to_tweets(client, tweet_ids, count)
                
                replied_ids = list(found_replies_set)
                unreplied_ids = list(set(tweet_ids) - found_replies_set)

                return ToolResponse.success({
                    'replied_ids': replied_ids,
                    'unreplied_ids': unreplied_ids
                })
            except Exception as e:
                return ToolResponse.fail(f"Failed to batch check reply status: {e}")
        
        # Other commands remain unchanged as they don't use the database
        elif command == 'browse_tweets':
            query = kwargs.get('query')
            if not query:
                return ToolResponse.fail("`query` is required for browse_tweets.")
            try:
                tweets = await client.search_tweet(query=query, product='Latest')
                tweet_data = [{
                    'id': t.id, 
                    'text': t.text, 
                    'user': {'id': t.user.id, 'name': t.user.name, 'screen_name': t.user.screen_name}
                } for t in tweets]
                return ToolResponse.success(tweet_data)
            except Exception as e:
                return ToolResponse.fail(f"Failed to browse tweets: {e}")
        
        elif command == 'get_my_info':
            try:
                user = await client.user()
                user_info = {
                    'id': user.id,
                    'name': user.name,
                    'screen_name': user.screen_name,
                    'followers_count': user.followers_count,
                    'following_count': user.following_count,
                    'description': user.description
                }
                return ToolResponse.success(user_info)
            except Exception as e:
                return ToolResponse.fail(f"Failed to get user info: {e}")

        elif command == 'like_tweet':
            tweet_id = kwargs.get('tweet_id')
            if not tweet_id:
                return ToolResponse.fail("`tweet_id` is required for like_tweet.")
            try:
                await client.favorite_tweet(tweet_id)
                return ToolResponse.success(f"Tweet {tweet_id} liked successfully.")
            except Exception as e:
                return ToolResponse.fail(f"Failed to like tweet {tweet_id}: {e}")

        elif command == 'retweet':
            tweet_id = kwargs.get('tweet_id')
            if not tweet_id:
                return ToolResponse.fail("`tweet_id` is required for retweet.")
            try:
                await client.retweet(tweet_id)
                return ToolResponse.success(f"Tweet {tweet_id} retweeted successfully.")
            except Exception as e:
                return ToolResponse.fail(f"Failed to retweet {tweet_id}: {e}")

        elif command == 'get_user_name_by_id':
            user_id = kwargs.get('user_id')
            if not user_id:
                return ToolResponse.fail("`user_id` is required for get_user_name_by_id.")
            try:
                user = await client.get_user(user_id)
                return ToolResponse.success({'user_id': user.id, 'name': user.name, 'screen_name': user.screen_name})
            except Exception as e:
                return ToolResponse.fail(f"Failed to get user name for ID {user_id}: {e}")

        elif command == 'get_tweet_replies':
            tweet_id = kwargs.get('tweet_id')
            if not tweet_id:
                return ToolResponse.fail("`tweet_id` is required for get_tweet_replies.")
            
            try:
                cursor = kwargs.get('cursor')
                # get_tweet_by_id can fetch the tweet and its replies simultaneously.
                # The cursor paginates through the replies.
                tweet_with_replies = await client.get_tweet_by_id(tweet_id, cursor=cursor)

                if not tweet_with_replies or not tweet_with_replies.replies:
                    return ToolResponse.success({'replies': [], 'next_cursor': None})

                replies_data = [{
                    'id': r.id,
                    'text': r.text,
                    'user': {'id': r.user.id, 'name': r.user.name, 'screen_name': r.user.screen_name},
                    'created_at': r.created_at
                } for r in tweet_with_replies.replies]

                return ToolResponse.success({
                    'replies': replies_data,
                    'next_cursor': tweet_with_replies.replies.next_cursor
                })
            except Exception as e:
                return ToolResponse.fail(f"Failed to get replies for tweet {tweet_id}: {e}")

        else:
            return ToolResponse.fail(f"Unknown command: {command}") 