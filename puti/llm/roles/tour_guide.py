"""
@Author: obstacles
@Time:  2025-03-27 14:18
@Description:  
"""
from llm.roles import Role, RoleType, McpRole
from typing import List, Literal
from llm.tools.talk import Reply
from llm.tools import BaseTool
from llm.tools.demo import GetFlightInfoArgs, GetFlightInfo, SearchResidentEvilInfo


class TourGuide(McpRole):
    """ role without any action """

    name: str = 'alex'
    skill: str = 'extensive travel knowledge'
    goal: str = "answer user questions"
    identity: RoleType = RoleType.ASSISTANT
    react_extra_demands: str = (
        'reply user in clear and easy to understand information in natural '
        'language rather than json structure, believe the result that intermediate action give to you'
    )
