"""
@Author: obstacles
@Time:  2025-06-19 15:14
@Description:  Actions for the X (Twitter) Bot
"""
from puti.llm.actions import Action, Template
from pydantic import Field, ConfigDict
from puti.llm.nodes import OpenAINode
from puti.llm.messages import UserMessage
from puti.logs import logger_factory
from typing import Union, Optional


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

        response = await super().run(role=role, previous_result=previous_result, *args, **kwargs)
        lgr.debug("Tweet publication completed")
        return response

