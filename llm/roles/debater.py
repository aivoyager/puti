"""
@Author: obstacles
@Time:  2025-03-13 11:05
@Description:  
"""
from llm.roles import Role, RoleType
from typing import List, Literal, Set
from llm.tools.talk import Reply
from llm.tools import BaseTool
from llm.roles.talker import PuTi
from llm.tools.debate import Debate


class Debater(Role):
    name: str = '乔治'
    sex: Literal['male', 'female'] = 'male'
    goal: str = "debate with someone else, trying to convince them according to turn-based speaking rules"
    think_extra_demands: str = ("You need to choose state right now, Here the rules."
                                "Speeches are made in the order of the alternating order of the debate, judging if its need you to speak from where you stand, "
                                "If NOT（wait for the other party to speak） then return -1 and do not think about anything else,"
                                "If YES then select the state number of other action")
    react_extra_demands: str = "Speeches are made in the order of the alternating order of the debate, You need to stand up for your own point of view to refute the other side's point of view"
    identity: RoleType = RoleType.USER

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_tools([Debate, Reply])
        self.set_interested_actions({Debate})

