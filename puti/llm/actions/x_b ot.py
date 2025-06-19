"""
@Author: obstacles
@Time:  2025-06-19 15:14
@Description:  Actions for the X (Twitter) Bot
"""
from puti.llm.actions import Action, Template
from pydantic import Field, ConfigDict
from puti.llm.nodes import OpenAINode
from puti.llm.messages import UserMessage


class GenerateTweetAction(Action):
    """
    An action to generate a topic, create a tweet, and review it.
    This encapsulates the entire content creation process using its own LLM node.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'generate_and_review_tweet'
    description: str = 'Generate a topic, create a new tweet, review it for quality, and return the final version.'
    
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
            "Make sure it's clear, engaging, and under 280 characters. "
            "If it's good, return it as is. If it needs improvement, return an improved version."
        ),
        description="Jinja2 template for the review step."
    )

    async def run(self, role, *args, **kwargs):
        """
        Executes the three-step topic-generation, tweet-creation, and review process.
        This action uses its own OpenAINode instance, ignoring the role's LLM.
        """
        # This action uses its own private LLM node instance
        llm_node = OpenAINode()

        # 1. Generate a topic
        topic_resp = await llm_node.chat([UserMessage(content=self.topic_prompt_template).to_message_dict()])
        generated_topic = topic_resp.content if hasattr(topic_resp, 'content') else str(topic_resp)

        # 2. Generate the initial tweet using the topic
        generation_prompt = self.generation_prompt_template.render(generated_topic=generated_topic)
        initial_tweet_resp = await llm_node.chat([UserMessage(content=generation_prompt).to_message_dict()])
        initial_tweet_content = initial_tweet_resp.content if hasattr(initial_tweet_resp, 'content') else str(initial_tweet_resp)

        # 3. Review the generated tweet
        review_prompt = self.review_prompt_template.render(generated_tweet=initial_tweet_content)
        final_tweet_resp = await llm_node.chat([UserMessage(content=review_prompt).to_message_dict()])

        return final_tweet_resp


class PublishTweetAction(Action):
    """
    An action to publish a finalized tweet.
    This action typically uses a tool to perform the posting.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'publish_tweet'
    description: str = 'Publishes the provided tweet content to Twitter.'
    
    prompt: Template = Field(
        default=Template("I will now post the following tweet: '{{ previous_result.content }}'"),
        description="Message confirming the tweet to be posted."
    ) 