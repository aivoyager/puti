"""
@Author: obstacles
@Time:  2025-03-07 14:41
@Description:  
"""
from llm.actions import Action
from pydantic import ConfigDict


class Talk(Action):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = 'Talk'
    desc: str = 'This Action for daily conversation'
