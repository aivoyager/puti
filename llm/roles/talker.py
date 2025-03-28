"""
@Author: obstacles
@Time:  2025-03-07 14:10
@Description:  
"""
from llm.roles import Role, RoleType
from typing import List, Literal
from llm.tools.talk import Reply
from llm.tools import BaseTool
from llm.tools.demo import GetFlightInfoArgs, GetFlightInfo, SearchResidentEvilInfo


class PuTi(Role):
    name: str = 'puti'
    skill: str = 'solving any task presented by the user'
    identity: RoleType = RoleType.ASSISTANT

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_tools([GetFlightInfo, Reply])
