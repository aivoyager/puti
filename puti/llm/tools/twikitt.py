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
        'check_reply_status_batch', 'get_tweet_replies', 'get_conversation_thread'
    ] = Field(
        ...,
        description='The command to run. Can be "send_tweet", "reply_to_tweet", "get_mentions", "has_my_reply", "check_reply_status_batch", "get_tweet_replies", "get_conversation_thread", etc.'
    )
    text: Optional[str] = Field(None, description='The text content for a tweet or reply.')
    tweet_id: Optional[str] = Field(None, description='The ID of a specific tweet for operations like replying, liking, retweeting, checking for a reply, or fetching replies.')
    tweet_ids: Optional[List[str]] = Field(None, description='A list of tweet IDs to check reply status for in batch operations like check_reply_status_batch or has_my_reply.')
    user_id: Optional[str] = Field(None, description='The ID of a user for lookup operations.')
    query: Optional[str] = Field(None, description='The keyword or content to search for tweets.')
    count: Optional[int] = Field(default=20, description='The number of items to retrieve. For reply checks, this is the number of your recent tweets to scan to find a reply.')
    start_time: Optional[str] = Field(None, description='The start time for fetching mentions, in ISO 8601 format (e.g., "2023-01-01T12:00:00Z"). Used with "get_mentions".')
    cursor: Optional[str] = Field(None, description='A pagination cursor to retrieve the next set of results for commands like "get_tweet_replies".')
    max_depth: Optional[int] = Field(default=5, description='The maximum depth to trace back in the conversation thread.')


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

    async def _check_reply_by_conversation(
        self, client: Client, tweet_id: str
    ) -> bool:
        """
        Check if the user has replied to a tweet by fetching the conversation/replies for that tweet.
        This is a more direct and accurate method than checking in_reply_to fields.
        
        Args:
            client: The Twitter client instance
            tweet_id: The ID of the tweet to check for replies
            
        Returns:
            bool: True if the user has replied to the tweet, False otherwise
        """
        try:
            # Get the authenticated user
            me = await client.user()
            
            # Get the conversation/replies for the tweet
            tweet_with_replies = await client.get_tweet_by_id(tweet_id)
            
            # If we couldn't fetch the tweet or it has no replies, return False
            if not tweet_with_replies or not tweet_with_replies.replies:
                return False
                
            # Check if any of the replies are from the current user
            for reply in tweet_with_replies.replies:
                if reply.user.id == me.id:
                    lgr.debug(f"Found direct reply to tweet {tweet_id} from user {me.id}")
                    return True
                    
            # No replies from the current user were found
            return False
            
        except Exception as e:
            lgr.error(f"Error checking replies for tweet {tweet_id}: {e}")
            return False  # Default to not replied on error

    async def _get_conversation_thread(
        self, client: Client, tweet_id: str, max_depth: int = 5
    ) -> dict:
        """
        Gets the full conversation thread for a tweet, tracing back to the original tweet
        and including all relevant context.
        
        Args:
            client: The Twitter client instance
            tweet_id: The ID of the tweet to get the conversation for
            max_depth: Maximum number of parent tweets to trace back
            
        Returns:
            dict: A dictionary containing the conversation thread with original tweet,
                  parent tweets, and any replies
        """
        try:
            conversation_thread = {
                "original_tweet": None,
                "parent_tweets": [],
                "current_tweet": None,
                "replies": []
            }
            
            # Get the current tweet
            current_tweet = await client.get_tweet_by_id(tweet_id)
            if not current_tweet:
                return conversation_thread
                
            conversation_thread["current_tweet"] = {
                "id": current_tweet.id,
                "text": current_tweet.text,
                "user": {
                    "id": current_tweet.user.id,
                    "name": current_tweet.user.name,
                    "screen_name": current_tweet.user.screen_name
                },
                "created_at": current_tweet.created_at
            }
            
            # If this tweet has replies, add them
            if current_tweet.replies:
                replies_data = [{
                    "id": r.id,
                    "text": r.text,
                    "user": {
                        "id": r.user.id,
                        "name": r.user.name,
                        "screen_name": r.user.screen_name
                    },
                    "created_at": r.created_at
                } for r in current_tweet.replies]
                
                conversation_thread["replies"] = replies_data
            
            # Trace back to parent tweets
            parent_id = current_tweet.in_reply_to
            depth = 0
            
            while parent_id and depth < max_depth:
                parent_tweet = await client.get_tweet_by_id(parent_id)
                if not parent_tweet:
                    break
                    
                parent_data = {
                    "id": parent_tweet.id,
                    "text": parent_tweet.text,
                    "user": {
                        "id": parent_tweet.user.id,
                        "name": parent_tweet.user.name,
                        "screen_name": parent_tweet.user.screen_name
                    },
                    "created_at": parent_tweet.created_at
                }
                
                # Add to the beginning of parent_tweets list to maintain chronological order
                conversation_thread["parent_tweets"].insert(0, parent_data)
                
                # If this is the first parent we find, it might be the original tweet
                if depth == 0 and not parent_tweet.in_reply_to:
                    conversation_thread["original_tweet"] = parent_data
                
                # Move up the chain
                parent_id = parent_tweet.in_reply_to
                depth += 1
            
            # If we didn't set the original tweet and we hit the depth limit,
            # use the oldest parent tweet we found as the original
            if not conversation_thread["original_tweet"] and conversation_thread["parent_tweets"]:
                conversation_thread["original_tweet"] = conversation_thread["parent_tweets"][0]
            
            # If there are no parent tweets, the current tweet is the original
            if not conversation_thread["parent_tweets"] and not conversation_thread["original_tweet"]:
                conversation_thread["original_tweet"] = conversation_thread["current_tweet"]
                
            return conversation_thread
            
        except Exception as e:
            lgr.error(f"Error getting conversation thread for tweet {tweet_id}: {e}")
            return {
                "original_tweet": None,
                "parent_tweets": [],
                "current_tweet": None,
                "replies": [],
                "error": str(e)
            }

    async def _check_my_replies_to_tweets(
        self, client: Client, tweet_ids_to_check: List[str], my_tweets_count: int
    ) -> set:
        """
        Checks which of the given tweet IDs have been replied to by the current user.
        
        This method fetches both the user's tweets and their replies, then examines the 
        'in_reply_to' field to determine which tweets in the provided list have already
        been replied to.
        """
        me = await client.user()
        
        # Fetch both regular tweets and replies to get comprehensive coverage
        my_tweets = await client.get_user_tweets(me.id, 'Tweets', count=my_tweets_count)
        my_replies = await client.get_user_tweets(me.id, 'Replies', count=my_tweets_count)
        
        # Combine both sets of tweets
        all_my_tweets = list(my_tweets) + list(my_replies)
        
        # Get the set of tweet IDs that the user has replied to
        replied_to_parent_ids = {
            tweet.in_reply_to for tweet in all_my_tweets if tweet.in_reply_to
        }
        
        # Log for debugging
        lgr.debug(f"Tweet IDs to check: {tweet_ids_to_check}")
        lgr.debug(f"Found regular tweets: {len(my_tweets)}")
        lgr.debug(f"Found reply tweets: {len(my_replies)}")
        lgr.debug(f"Total tweets examined: {len(all_my_tweets)}")
        lgr.debug(f"Found replied_to_parent_ids: {replied_to_parent_ids}")

        # Find the intersection - these are the tweets that the user has replied to
        found_replied_ids = set(tweet_ids_to_check) & replied_to_parent_ids
        lgr.debug(f"Intersection (found_replied_ids): {found_replied_ids}")
        
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

        if command == 'send_tweet':  # TODO：media support
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
                # First, check if we've already replied by looking at our replies directly
                count = kwargs.get('count', 500)
                me = await client.user()
                
                # Get the user's replies specifically
                my_replies = await client.get_user_tweets(me.id, 'Replies', count=count)
                
                # Check if any of these replies are to the tweet we're looking for
                already_replied = any(reply.in_reply_to == tweet_id for reply in my_replies)
                
                # If we didn't find it through direct replies, try the comprehensive method
                if not already_replied:
                    lgr.debug(f"No direct reply found for tweet {tweet_id}, trying comprehensive check")
                    found_replies = await self._check_my_replies_to_tweets(client, [tweet_id], count)
                    already_replied = bool(found_replies)
                
                # If we still didn't find it, try the conversation check as a last resort
                if not already_replied:
                    lgr.debug(f"No reply found in user's tweets for {tweet_id}, trying conversation check")
                    already_replied = await self._check_reply_by_conversation(client, tweet_id)
                
                if already_replied:
                    return ToolResponse.success(f"You have already replied to tweet {tweet_id}.")

                # If we haven't replied yet, send the reply
                reply_tweet = await client.create_tweet(text=text, reply_to=tweet_id)
                return ToolResponse.success(f"Reply sent successfully to tweet {tweet_id}: {reply_tweet.id}")
            except Exception as e:
                lgr.error(f"Failed to reply to tweet: {e}", exc_info=True)
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
            # Support both single tweet_id and batch tweet_ids
            tweet_id = kwargs.get('tweet_id')
            tweet_ids = kwargs.get('tweet_ids')
            
            # Handle both single ID and list of IDs
            if tweet_id and not tweet_ids:
                # Convert single ID to list for consistent processing
                tweet_ids = [tweet_id]
            elif not tweet_ids:
                return ToolResponse.fail("Either `tweet_id` or `tweet_ids` is required for has_my_reply.")
            
            try:
                count = kwargs.get('count', 500)
                me = await client.user()
                
                # Step 1: First check directly against replies - fastest and most accurate
                my_replies = await client.get_user_tweets(me.id, 'Replies', count=count)
                
                # Create a set of tweets we've directly replied to
                direct_replies_set = set()
                for reply in my_replies:
                    if reply.in_reply_to and reply.in_reply_to in tweet_ids:
                        direct_replies_set.add(reply.in_reply_to)
                
                lgr.debug(f"Direct reply check found {len(direct_replies_set)} replied tweets")
                
                # Step 2: For tweets we didn't find direct replies to, use the comprehensive method
                remaining_tweets = set(tweet_ids) - direct_replies_set
                
                if remaining_tweets:
                    lgr.debug(f"Checking {len(remaining_tweets)} remaining tweets with comprehensive method")
                    additional_replies_set = await self._check_my_replies_to_tweets(client, list(remaining_tweets), count)
                    lgr.debug(f"Comprehensive check found {len(additional_replies_set)} additional replied tweets")
                else:
                    additional_replies_set = set()
                
                # Step 3: For any still not found, do the direct conversation check
                # This is more expensive, so we only do it if we have a reasonable number of tweets left
                final_remaining = remaining_tweets - additional_replies_set
                conversation_replies_set = set()
                
                # Only do conversation checks if we have 5 or fewer tweets to check
                # to avoid making too many API calls
                if final_remaining and len(final_remaining) <= 5:
                    lgr.debug(f"Checking {len(final_remaining)} remaining tweets with conversation method")
                    for tweet_id in final_remaining:
                        has_reply = await self._check_reply_by_conversation(client, tweet_id)
                        if has_reply:
                            conversation_replies_set.add(tweet_id)
                    
                    lgr.debug(f"Conversation check found {len(conversation_replies_set)} additional replied tweets")
                
                # Combine all replied tweets from the three methods
                all_replied_ids = direct_replies_set | additional_replies_set | conversation_replies_set
                unreplied_ids = set(tweet_ids) - all_replied_ids
                
                # Create result for each tweet ID
                results = {}
                for tid in tweet_ids:
                    reply_found = tid in all_replied_ids
                    method = None
                    if tid in direct_replies_set:
                        method = "direct"
                    elif tid in additional_replies_set:
                        method = "comprehensive"
                    elif tid in conversation_replies_set:
                        method = "conversation"
                    
                    results[tid] = {
                        "has_reply": reply_found,
                        "method": method if reply_found else None
                    }
                
                # For backwards compatibility, if there was only one tweet_id, include the single result format
                response = {
                    "tweet_ids": tweet_ids,
                    "results": results,
                    "replied_ids": list(all_replied_ids),
                    "unreplied_ids": list(unreplied_ids),
                    "reply_counts": {
                        "direct": len(direct_replies_set),
                        "comprehensive": len(additional_replies_set),
                        "conversation": len(conversation_replies_set),
                        "total": len(all_replied_ids)
                    }
                }
                
                # If this was a single tweet_id request, add simplified format for backwards compatibility
                if len(tweet_ids) == 1:
                    response["tweet_id"] = tweet_ids[0]
                    response["has_my_reply"] = results[tweet_ids[0]]["has_reply"]
                
                return ToolResponse.success(response)
            except Exception as e:
                lgr.error(f"Failed to check reply status for tweets {tweet_ids}: {e}", exc_info=True)
                return ToolResponse.fail(f"Failed to check reply status for tweets {tweet_ids}: {e}")

        elif command == 'check_reply_status_batch':
            tweet_ids = kwargs.get('tweet_ids')
            if not tweet_ids:
                return ToolResponse.fail("`tweet_ids` list is required.")

            try:
                count = kwargs.get('count', 500)  # Increased from default 200
                me = await client.user()
                
                # Step 1: First check directly against replies - this is fast and most accurate
                my_replies = await client.get_user_tweets(me.id, 'Replies', count=count)
                
                # Create a set of tweets we've directly replied to
                direct_replies_set = set()
                for reply in my_replies:
                    if reply.in_reply_to and reply.in_reply_to in tweet_ids:
                        direct_replies_set.add(reply.in_reply_to)
                
                lgr.debug(f"Direct reply check found {len(direct_replies_set)} replied tweets")
                
                # Step 2: For tweets we didn't find direct replies to, use the comprehensive method
                remaining_tweets = set(tweet_ids) - direct_replies_set
                
                if remaining_tweets:
                    lgr.debug(f"Checking {len(remaining_tweets)} remaining tweets with comprehensive method")
                    additional_replies_set = await self._check_my_replies_to_tweets(client, list(remaining_tweets), count)
                    lgr.debug(f"Comprehensive check found {len(additional_replies_set)} additional replied tweets")
                else:
                    additional_replies_set = set()
                
                # Step 3: For any still not found, do the direct conversation check
                final_remaining = remaining_tweets - additional_replies_set
                conversation_replies_set = set()
                
                if final_remaining:
                    lgr.debug(f"Checking {len(final_remaining)} remaining tweets with conversation method")
                    for tweet_id in final_remaining:
                        has_reply = await self._check_reply_by_conversation(client, tweet_id)
                        if has_reply:
                            conversation_replies_set.add(tweet_id)
                    
                    lgr.debug(f"Conversation check found {len(conversation_replies_set)} additional replied tweets")
                
                # Combine all replied tweets from the three methods
                all_replied_ids = direct_replies_set | additional_replies_set | conversation_replies_set
                unreplied_ids = set(tweet_ids) - all_replied_ids
                
                # Convert to lists for the response
                replied_ids = list(all_replied_ids)
                unreplied_ids = list(unreplied_ids)
                
                # Log the final results
                lgr.debug(f"check_reply_status_batch final results:")
                lgr.debug(f"- Direct replies: {len(direct_replies_set)}")
                lgr.debug(f"- Additional via comprehensive check: {len(additional_replies_set)}")
                lgr.debug(f"- Additional via conversation check: {len(conversation_replies_set)}")
                lgr.debug(f"- Total replied: {len(replied_ids)}")
                lgr.debug(f"- Unreplied: {len(unreplied_ids)}")

                return ToolResponse.success({
                    'replied_ids': replied_ids,
                    'unreplied_ids': unreplied_ids,
                    'reply_counts': {
                        'direct': len(direct_replies_set),
                        'comprehensive': len(additional_replies_set),
                        'conversation': len(conversation_replies_set)
                    }
                })
            except Exception as e:
                lgr.error(f"Failed to batch check reply status: {e}", exc_info=True)
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

        elif command == 'get_conversation_thread':
            tweet_id = kwargs.get('tweet_id')
            if not tweet_id:
                return ToolResponse.fail("`tweet_id` is required for get_conversation_thread.")
            
            try:
                # Optional parameter for maximum depth to trace back
                max_depth = kwargs.get('max_depth', 5)
                
                # Get the full conversation thread using our helper method
                conversation_thread = await self._get_conversation_thread(
                    client, 
                    tweet_id,
                    max_depth=max_depth
                )
                
                return ToolResponse.success(conversation_thread)
            except Exception as e:
                return ToolResponse.fail(f"Failed to get conversation thread for tweet {tweet_id}: {e}")

        else:
            return ToolResponse.fail(f"Unknown command: {command}") 