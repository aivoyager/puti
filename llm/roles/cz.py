"""
@Author: obstacles
@Time:  2025-04-09 16:32
@Description:  
"""

from llm.roles import Role
from llm.tools.generate_tweet import GenerateTweet


class CZ(Role):
    name: str = 'cz or 赵长鹏 or changpeng zhao'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_tools([GenerateTweet])


