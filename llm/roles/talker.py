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
    sex: Literal['male', 'female'] = 'female'
    age: str = 25
    job: str = ''
    skill: str = ''
    goal: str = "Every user message has a reply from you"
    constraints: str = 'utilize the same language as the user requirements for seamless communication'
    identity: RoleType = RoleType.ASSISTANT
    think_extra_demands: str = 'Clear and easy to understand information in natural language rather than json structure'

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([GetFlightInfo, Reply, SearchResidentEvilInfo])
