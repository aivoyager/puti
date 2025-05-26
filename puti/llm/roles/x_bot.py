"""
@Author: obstacles
@Time:  2025-05-21 11:15
@Description:  
"""
from typing import Any

from puti.llm.roles import Role
from pydantic import Field, ConfigDict


class TwitWhiz(Role):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'TwitWhiz'
    skill: str = (
        'Instantly generating friendly and witty replies to tweets,'
        'Staying on-topic while adding a cheerful tone,'
        'Responding with natural language that feels human, not robotic,'
        'Keeping responses under 280 characters,'
        'Using emojis and humor tastefully to boost engagement,'
        'Adapting tone based on the original tweet’s mood'
    )

    def model_post_init(self, __context: Any) -> None:
        self.agent_node.conf.MODEL = 'gpt-4.5-preview'
