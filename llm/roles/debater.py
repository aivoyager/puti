"""
@Author: obstacles
@Time:  2025-03-13 11:05
@Description:  
"""
from llm.roles import Role, RoleType
from typing import List, Literal, Set
from llm.actions.talk import Reply
from llm.actions import Action
from llm.roles.talker import Talker
from llm.actions.debate import Debate


class Debater(Role):
    name: str = '乔治'
    sex: Literal['male', 'female'] = 'male'
    goal: str = "debate with someone else, trying to convince them according to turn-based speaking rules"
    extra_demands: str = "The speeches in the debate are round rank, Judge whether you have spoken according to your position, if you have already spoken, then return -1 and do not think about anything else"
    identity: RoleType = RoleType.USER

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([Debate, Reply])
        self.set_interested_actions({Debate})

