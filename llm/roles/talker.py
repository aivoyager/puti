"""
@Author: obstacles
@Time:  2025-03-07 14:10
@Description:  
"""
from llm.roles import Role, RoleType
from typing import List, Literal
from llm.actions.talk import Reply
from llm.actions import Action
from llm.actions.get_flight_time import GetFlightInfoArgs, GetFlightInfo, SearchResidentEvilInfo


class Talker(Role):
    name: str = 'obstalces'
    skill: str = 'communication'
    goal: str = "every user message has a reply from you"
    identity: RoleType = RoleType.ASSISTANT
    react_extra_demands: str = (
        'reply user in clear and easy to understand information in natural '
        'language rather than json structure, believe the result that intermediate action give to you')

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([GetFlightInfo, Reply, SearchResidentEvilInfo])
