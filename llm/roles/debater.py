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
    think_extra_demands: str = ("You need to choose state right now, Here the rules."
                                " The speeches in the debate are round rank, judging from where you stand, if you have already spoken and the other party has no new counter-arguments, wait for the other party to speak, then return -1 and do not think about anything else")
    react_extra_demands: str = "Speeches are made in the order of the alternating order of the debate"
    identity: RoleType = RoleType.USER

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([Debate, Reply])
        self.set_interested_actions({Debate})

