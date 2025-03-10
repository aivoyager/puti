"""
@Author: obstacles
@Time:  2025-03-07 14:10
@Description:  
"""
from llm.roles import Role
from typing import List, Literal
from llm.actions.talk import Talk
from llm.actions import Action


class Talker(Role):
    name: str = 'obstalces'
    sex: Literal['male', 'female'] = 'female'
    age: str = 25
    job: str = 'Communicator'
    skill: str = 'Communicate'
    goal: str = 'Help others by communicating with them.'
    constraints: str = ''

    actions: List[Action] = []
    state: List[str] = []

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([Talk])

