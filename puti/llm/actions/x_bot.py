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
    An action to reply to a tweet with awareness of the full conversation context.
    This action retrieves the full conversation thread before generating and sending a reply.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'context_aware_reply'
    description: str = 'Generates and sends a reply to a tweet with full conversation context awareness.'
    
    tweet_id: str = Field(..., description="The ID of the tweet to reply to")
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
    
    async def run(self, role, *args, **kwargs):
        """
        Executes the context-aware reply process:
        1. Retrieves the full conversation thread for the tweet
        2. Generates a contextually appropriate reply
        3. Sends the reply
        
        Args:
            role: The agent role that will perform the actions
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
            
        Returns:
            The response from sending the reply
        """
        try:
            
            lgr.info(f"Starting context-aware reply for tweet {self.tweet_id}")
            
            # Step 1: Get the conversation thread
            # Instead of using use_tool directly, we create a prompt for the agent
            # to use the Twikitt tool to get the conversation thread
            get_thread_prompt = f"""Use the twikitt tool with the get_conversation_thread command to retrieve the full conversation thread for tweet ID {self.tweet_id}. Set max_depth={self.max_context_depth}. The result should be a JSON string."""
            
            # Run the agent to get the conversation thread
            thread_response = await role.run(get_thread_prompt)
            
            # Process the response to extract the thread data
            # This requires parsing the JSON from the response
            try:
                # Try to extract JSON from the response string
                
                # Look for JSON object in the response
                json_match = re.search(r'```json\n(.*?)\n```', thread_response, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'{.*}', thread_response, re.DOTALL)
                    
                if json_match:
                    thread_data_str = json_match.group(1) if '```' in json_match.group(0) else json_match.group(0)
                    thread_data = json.loads(thread_data_str)
                else:
                    # If we can't extract JSON, use a simplified approach
                    lgr.warning(f"Could not extract thread data from response: {thread_response}")
                    # Create a simple thread structure with just the current tweet
                    thread_data = {
                        "original_tweet": None,
                        "parent_tweets": [],
                        "current_tweet": {
                            "id": self.tweet_id,
                            "text": "Tweet content not available",
                            "user": {
                                "id": "unknown",
                                "name": "Twitter User",
                                "screen_name": "user"
                            }
                        },
                        "replies": []
                    }
            except Exception as e:
                lgr.error(f"Error parsing thread data: {e}")
                # Simplified thread structure as fallback
                thread_data = {
                    "original_tweet": None,
                    "parent_tweets": [],
                    "current_tweet": {
                        "id": self.tweet_id,
                        "text": "Tweet content not available",
                        "user": {
                            "id": "unknown",
                            "name": "Twitter User",
                            "screen_name": "user"
                        }
                    },
                    "replies": []
                }
            
            # Step 2: Generate reply using the conversation context
            prompt = self.prompt.render(
                original_tweet=thread_data.get("original_tweet"),
                parent_tweets=thread_data.get("parent_tweets", []),
                current_tweet=thread_data.get("current_tweet")
            )
            
            # Use the agent to generate a contextual reply
            reply_generation = await role.run(prompt)
            
            # Extract the reply text - should be the direct output from the agent
            reply_text = reply_generation
            
            # Make sure reply is within Twitter character limit
            if len(reply_text) > 280:
                lgr.warning(f"Generated reply exceeds 280 characters, truncating: {reply_text}")
                reply_text = reply_text[:277] + "..."
            
            # Step 3: Send the reply
            reply_prompt = f"""Use the twikitt tool with the reply_to_tweet command to reply to tweet ID {self.tweet_id} with the following text:
            
"{reply_text}"
"""
            
            # Run the agent to send the reply
            reply_response = await role.run(reply_prompt)
            
            return reply_response
            
        except Exception as e:
            lgr.error(f"Error in context-aware reply action: {str(e)}")
            return f"Error in context-aware reply: {str(e)}"


class ContextAwareReplyToMentionsAction(Action):
    """
    An action that finds unreplied mentions and replies to them with full conversation context awareness.
    This combines finding mentions with context-aware replies.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'context_aware_reply_to_mentions'
    description: str = 'Finds and replies to unreplied mentions with full conversation context awareness.'
    
    time_value: int = Field(default=7, description="The number of time units to look back (e.g., 7).")
    time_unit: Literal['days', 'hours'] = Field(default='days', description="The unit of time, either 'days' or 'hours'.")
    max_context_depth: int = Field(default=5, description="Maximum depth for tracing conversation history")
    max_mentions: int = Field(default=5, description="Maximum number of mentions to process")
    
    prompt: Template = Field(default=Template(
        """Find all tweets from the last {{ time_value }} {{ time_unit }} that mention me and have not been replied to yet. List them in chronological order (oldest first), showing the tweet ID, author, and content."""
    ), description="Template for finding unreplied mentions")
    
    async def run(self, role, *args, **kwargs):
        """
        Executes the context-aware reply to mentions process:
        1. Finds unreplied mentions within the specified time frame
        2. For each mention, gets the full conversation context
        3. Generates and sends a contextually appropriate reply
        
        Args:
            role: The agent role that will perform the actions
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
            
        Returns:
            Summary of actions taken
        """
        lgr.info(f"Starting context-aware replies to mentions from last {self.time_value} {self.time_unit}")
        
        # Format the time for the query
        time_ago = None
        if self.time_unit == 'days':
            time_ago = (datetime.datetime.now() - datetime.timedelta(days=self.time_value)).isoformat()
        elif self.time_unit == 'hours':
            time_ago = (datetime.datetime.now() - datetime.timedelta(hours=self.time_value)).isoformat()
        
        try:
            # Step 1: Get unreplied mentions
            mentions_prompt = self.prompt.render(
                time_value=self.time_value,
                time_unit=self.time_unit
            )
            
            # Run the agent to get mentions
            mentions_response = await role.run(mentions_prompt)
            
            # Parse the response to extract mention IDs
            
            # Look for JSON array or mention IDs in the response
            mention_ids = []
            
            # Try to extract JSON from the response
            lgr.info(f"Mentions response: {mentions_response[:200]}...")
            
            # First try with standard JSON code block format
            json_match = re.search(r'```json\s*(.*?)\s*```', mentions_response, re.DOTALL)
            
            # If that fails, try with a more flexible pattern that can handle indentation
            if not json_match:
                json_match = re.search(r'```json\s*\n\s*(\[.*?\])\s*\n\s*```', mentions_response, re.DOTALL)
            
            # If that still fails, try to find any JSON array
            if not json_match:
                json_match = re.search(r'\[\s*{.*?}\s*(?:,\s*{.*?}\s*)*\]', mentions_response, re.DOTALL)
                
            if json_match:
                lgr.info(f"Found JSON match in response")
                try:
                    json_str = json_match.group(1) if '```' in json_match.group(0) else json_match.group(0)
                    # Remove leading/trailing whitespace and normalize indentation
                    json_str = re.sub(r'^\s+', '', json_str, flags=re.MULTILINE)
                    lgr.info(f"Extracted JSON string: {json_str[:100]}...")
                    
                    mentions_data = json.loads(json_str)
                    lgr.info(f"Parsed mentions data: {mentions_data}")
                    if isinstance(mentions_data, list):
                        for mention in mentions_data:
                            if isinstance(mention, dict) and 'mention_id' in mention:
                                mention_ids.append(mention['mention_id'])
                except Exception as e:
                    lgr.error(f"Error parsing mentions JSON: {e}")
                    lgr.error(f"JSON string that failed to parse: {json_str if 'json_str' in locals() else 'Not extracted'}")
            
            # If JSON extraction failed, try to find mention IDs in the text
            if not mention_ids:
                lgr.info("JSON extraction failed, trying to find mention IDs in text")
                # Look for patterns like "ID: 123456789" or "mention_id: 123456789"
                id_matches = re.findall(r'(?:ID|id|mention_id):\s*(\d+)', mentions_response)
                lgr.info(f"Found ID matches: {id_matches}")
                mention_ids.extend(id_matches)
            
            # Limit the number of mentions to process
            mention_ids = mention_ids[:self.max_mentions]
            
            if not mention_ids:
                return "No unreplied mentions found."
            
            # Step 2: Reply to each unreplied mention with context awareness
            results = []
            for tweet_id in mention_ids:
                # Create and run a context-aware reply action for this mention
                context_action = ContextAwareReplyAction(
                    tweet_id=tweet_id,
                    max_context_depth=self.max_context_depth
                )
                
                reply_result = await context_action.run(role)
                
                # Store the result
                results.append({
                    'tweet_id': tweet_id,
                    'result': str(reply_result)
                })
                
                # Add a small delay between API calls to avoid rate limits
                await asyncio.sleep(2)
            
            # Step 3: Summarize the results
            summary = f"Processed {len(results)} unreplied mentions:\n"
            for result in results:
                summary += f"- Tweet {result['tweet_id']}: Replied\n"
            
            lgr.info(summary)
            return summary
            
        except Exception as e:
            lgr.error(f"Error in context-aware reply to mentions action: {str(e)}")
            return f"Error in context-aware reply to mentions: {str(e)}"
