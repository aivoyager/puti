"""
@Author: obstacles
@Time:  2025-03-13 11:05
@Description:  
"""
from typing import Any
from puti.llm.roles import Role
from puti.llm.tools.web_search import WebSearch


class Debater(Role):
    name: str = '乔治'
    skill: str = ("debate contest. "
                  "As a debater, You can't make the same argument every round and stand your ground "
                  "and give your argument process")

    def model_post_init(self, __context: Any) -> None:
        self.set_tools([WebSearch])

