"""
@Author: obstacles
@Time: 2024-08-10
@Description: Actions for X (Twitter) bot
"""
import datetime
import json
import re
import asyncio
from typing import List, Optional, Literal, Union, Dict, Any
from pydantic import Field, ConfigDict
from jinja2 import Template

from puti.logs import logger_factory
from puti.llm.actions import Action
from puti.llm.graph import Graph, Vertex
from puti.llm.roles.agents import Ethan
from puti.llm.nodes import OpenAINode
from puti.llm.messages import UserMessage

lgr = logger_factory.llm


class GenerateTweetAction(Action):
    """
    An action to generate a topic, create a tweet, and review it.
    This encapsulates the entire content creation process using its own LLM node.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'generate_and_review_tweet'
    description: str = 'Generate a topic, create a new tweet, review it for quality, and return the final version.'

    topic: Optional[str] = Field(default='', description="Optional topic to use for generating the tweet.")

    topic_prompt_template: str = Field(
        default="Generate a trending topic or interesting insight about AI, tech, or programming that would be valuable to tweet about today.",
        description="The prompt to generate a topic for the tweet."
    )
    
    generation_prompt_template: Template = Field(
        default=Template(
            "Generate a tweet about {{ generated_topic }}. "
            "The tweet should be engaging, informative, and under 280 characters."
        ),
        description="Jinja2 template for generating the initial tweet."
    )
    
    review_prompt_template: Template = Field(
        default=Template(
            "Review this tweet: '{{ generated_tweet }}'. "
            "Make sure it's clear, engaging, between 100 and 280 characters. "
            "If it's good, return it as is. If it needs improvement, return an improved version."
            "Give tweet only without other redundant."
        ),
        description="Jinja2 template for the review step."
    )

    async def run(self, *args, **kwargs):
        """
        Executes the three-step topic-generation, tweet-creation, and review process.
        This action uses its own OpenAINode instance, ignoring the role's LLM.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments including possible topic parameter
        """
        lgr.info(f"Starting tweet generation process with {self.name} action")

        if kwargs.get('topic'):
            self.topic = kwargs.get('topic')

        llm_node = OpenAINode()

        # 1. Generate a topic (use provided topic if given)
        if self.topic:
            generated_topic = self.topic
        else:
            topic_resp = await llm_node.chat([UserMessage(content=self.topic_prompt_template).to_message_dict()])
            generated_topic = topic_resp.content if hasattr(topic_resp, 'content') else str(topic_resp)

        # 2. Generate the initial tweet using the topic
        generation_prompt = self.generation_prompt_template.render(generated_topic=generated_topic)
        initial_tweet_resp = await llm_node.chat([UserMessage(content=generation_prompt).to_message_dict()])
        initial_tweet_content = initial_tweet_resp.content if hasattr(initial_tweet_resp, 'content') else str(initial_tweet_resp)

        # 3. Review the generated tweet
        review_prompt = self.review_prompt_template.render(generated_tweet=initial_tweet_content)
        final_tweet_resp = await llm_node.chat([UserMessage(content=review_prompt).to_message_dict()])
        
        final_content = final_tweet_resp.content if hasattr(final_tweet_resp, 'content') else str(final_tweet_resp)
        lgr.debug(f"Final tweet generated: {final_content}")

        return final_tweet_resp


class PublishTweetAction(Action):
    """
    An action to publish a finalized tweet.
    This action typically uses a tool to perform the posting.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'publish_tweet'
    description: str = 'Publishes the provided tweet content to Twitter.'
    
    prompt: Union[Template, str] = Field(
        default=Template("post the following tweet: '{{ previous_result }}'"),
        description="Message confirming the tweet to be posted."
    )
    
    async def run(self, role, previous_result=None, *args, **kwargs):
        if previous_result:
            tweet_content = previous_result.content if hasattr(previous_result, 'content') else str(previous_result)
        else:
            tweet_content = None

        response = await super().run(role=role, previous_result=tweet_content, *args, **kwargs)
        lgr.debug("Tweet publication completed")
        return response


class ReplyToRecentUnrepliedTweetsAction(Action):
    """
    An action to find and reply to unreplied tweets within a specified time frame.
    This action instructs an agent (like Ethan) to perform the task.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'reply_to_recent_unreplied_tweets'
    description: str = 'Finds and replies to unreplied tweets from the last n days or n hours.'

    time_value: int = Field(default=7, description="The number of time units to look back (e.g., 7).")
    time_unit: Literal['days', 'hours'] = Field(default='days', description="The unit of time, either 'days' or 'hours'.")
    prompt: Union[Template, str] = Field(default=Template(
        """Find all tweets from the last {{ final_time_value }} {{ final_time_unit }} that mention me,and have not been replied to. For each of these tweets, please draft and send a thoughtful reply."""
    ), description="Template for the reply prompt.")

    async def run(self, role, *args, **kwargs):
        self.prompt = self.prompt.render(
            final_time_value=self.time_value,
            final_time_unit=self.time_unit
        )
        response = await super().run(role=role, *args, **kwargs)
        lgr.debug("Reply to unreplied tweets completed")
        return response


class ContextAwareReplyAction(Action):
    """
    An action to reply to one or more tweets with awareness of the full conversation context.
    This action retrieves the full conversation thread for each tweet before generating and sending a reply.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'context_aware_reply'
    description: str = 'Generates and sends context-aware replies to a batch of tweets.'
    
    tweet_ids: Optional[List[str]] = Field(default=None, description="A list of tweet IDs to reply to. If not provided, it will be taken from the previous action's result.")
    max_context_depth: int = Field(default=5, description="Maximum depth for tracing conversation history")
    
    prompt: Template = Field(default=Template(
        """I need to reply to a tweet in a conversation thread. Here's the full context:
        
{% if original_tweet %}
ORIGINAL TWEET ({{ original_tweet.user.name }} @{{ original_tweet.user.screen_name }}):
{{ original_tweet.text }}
{% endif %}

{% if parent_tweets %}
CONVERSATION HISTORY:
{% for tweet in parent_tweets %}
{{ tweet.user.name }} @{{ tweet.user.screen_name }}:
{{ tweet.text }}

{% endfor %}
{% endif %}

TWEET TO REPLY TO ({{ current_tweet.user.name }} @{{ current_tweet.user.screen_name }}):
{{ current_tweet.text }}

Please draft a thoughtful, relevant reply that considers the full conversation context.
The reply should be concise (under 280 characters), engaging, and directly address the points in the tweet.
"""
    ), description="Template for generating the reply with context")
    
    async def run(self, role, previous_result=None, *args, **kwargs):
        """
        Executes the context-aware reply process for each tweet in the list.
        
        Args:
            role: The agent role that will perform the actions
            previous_result: The result from the previous action, expected to be a list of tweet IDs.
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
            
        Returns:
            A summary of the reply actions taken.
        """
        tweet_ids_to_process = self.tweet_ids
        if not tweet_ids_to_process and previous_result:
            if isinstance(previous_result, list):
                tweet_ids_to_process = previous_result
            else:
                lgr.info(f"Previous result is not a list, attempting to parse IDs from string: {previous_result}")
                tweet_ids_to_process = re.findall(r'\d{18,}', str(previous_result))

        if not tweet_ids_to_process:
            return "No tweet IDs provided or found from previous step. Nothing to do."

        results = []
        lgr.info(f"Starting batch context-aware reply for {len(tweet_ids_to_process)} tweets.")

        for tweet_id in tweet_ids_to_process:
            try:
                lgr.info(f"Processing tweet ID: {tweet_id}")
                
                # Step 1: Get the conversation thread
                get_thread_prompt = f"""Use the twikitt tool with the get_conversation_thread command to retrieve the full conversation thread for tweet ID {tweet_id}. Set max_depth={self.max_context_depth}. The result should be a JSON string."""
                thread_response = await role.run(get_thread_prompt)
                
                # Step 2: Parse thread data
                thread_data = {}
                try:
                    json_match = re.search(r'```json\n(.*?)\n```', thread_response, re.DOTALL)
                    if not json_match:
                        json_match = re.search(r'{.*}', thread_response, re.DOTALL)
                    
                    if json_match:
                        thread_data_str = json_match.group(1) if '```' in json_match.group(0) else json_match.group(0)
                        thread_data = json.loads(thread_data_str)
                    else:
                        lgr.warning(f"Could not extract thread data for tweet {tweet_id} from response: {thread_response}")
                except Exception as e:
                    lgr.error(f"Error parsing thread data for tweet {tweet_id}: {e}")

                # Step 3: Generate reply
                generation_prompt = self.prompt.render(
                    original_tweet=thread_data.get("original_tweet"),
                    parent_tweets=thread_data.get("parent_tweets", []),
                    current_tweet=thread_data.get("current_tweet", {"id": tweet_id, "text": "Content not available", "user": {"name": "Unknown", "screen_name": "unknown"}})
                )
                reply_text = await role.run(generation_prompt)
                
                if len(reply_text) > 280:
                    reply_text = reply_text[:277] + "..."

                # Step 4: Send the reply
                reply_prompt = f"""Use the twikitt tool with the reply_to_tweet command to reply to tweet ID {tweet_id} with the following text:
                
"{reply_text}"
"""
                reply_response = await role.run(reply_prompt)
                
                results.append({"tweet_id": tweet_id, "status": "success", "response": reply_response})
                lgr.info(f"Successfully sent reply to tweet {tweet_id}.")

            except Exception as e:
                error_message = f"Failed to process tweet {tweet_id}: {e}"
                lgr.error(error_message, exc_info=True)
                results.append({"tweet_id": tweet_id, "status": "error", "response": error_message})
            
            # Add a small delay between replies to avoid rate limiting
            await asyncio.sleep(2)

        # Summarize the results
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = len(results) - success_count
        summary = f"Batch reply finished. Success: {success_count}, Failed: {error_count}.\n"
        for res in results:
            summary += f"- Tweet {res['tweet_id']}: {res['status']}\n"
            
        return summary


class GetUnrepliedMentionsAction(Action):
    """
    An action that finds recent, unreplied mentions and returns their IDs.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'get_unreplied_mentions'
    description: str = 'Finds and returns a list of tweet IDs for recent, unreplied mentions.'
    
    time_value: int = Field(default=24, description="The number of time units to look back (e.g., 24).")
    time_unit: Literal['days', 'hours'] = Field(default='hours', description="The unit of time, either 'days' or 'hours'.")
    max_mentions: int = Field(default=3, description="Maximum number of mention IDs to return.")
    
    prompt: Template = Field(default=Template(
        """Find up to {{ max_mentions }} recent tweets mentioning me from the last {{ time_value }} {{ time_unit }} that I haven't replied to yet. 
        
        Use the twikitt tool with the get_mentions command to retrieve recent mentions.
        Then check which ones I haven't replied to yet.
        
        Return a Python-style list of the tweet IDs as strings, and nothing else. For example: ['123456789012345678', '123456789012345679']"""
    ), description="Template for finding unreplied mentions.")
    
    async def run(self, role, *args, **kwargs):
        """
        Executes the process of finding unreplied mentions using the role's LLM capabilities.
        
        Args:
            role: The agent role that will perform the actions.
            
        Returns:
            A list of tweet IDs.
        """
        lgr.info(f"Finding up to {self.max_mentions} unreplied mentions from the last {self.time_value} {self.time_unit}.")
        
        # Generate the prompt for the LLM
        prompt_str = self.prompt.render(
            max_mentions=self.max_mentions,
            time_value=self.time_value,
            time_unit=self.time_unit
        )
        
        # Ask the role (Ethan) to get unreplied mentions
        response = await role.run(prompt_str)
        
        # Extract tweet IDs from the response string
        tweet_ids = re.findall(r'\'(\d{18,})\'|\"(\d{18,})\"', str(response))
        # re.findall with groups returns tuples, so we need to flatten the list
        extracted_ids = [item for tpl in tweet_ids for item in tpl if item]

        if not extracted_ids:
            lgr.warning(f"Could not extract any tweet IDs from response: {response}")
            return []
            
        lgr.info(f"Found {len(extracted_ids)} unreplied mention(s): {extracted_ids}")
        return extracted_ids
