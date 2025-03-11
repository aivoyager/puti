"""
@Author: obstacles
@Time:  2025-03-07 14:10
@Description:  
"""
from llm.roles import Role, RoleType
from typing import List, Literal
from llm.actions.talk import Reply
from llm.actions import Action


class Talker(Role):
    name: str = 'obstalces'
    sex: Literal['male', 'female'] = 'female'
    age: str = 25
    job: str = 'communicator'
    skill: str = 'communicate'
    goal: str = "reply unanswered user messages"
    constraints: str = 'utilize the same language as the user requirements for seamless communication'
    #  when the latest entry in the chat history is not you (obstalces) (case insensitive) and the role_type of the message is user
    identity: RoleType = RoleType.ASSISTANT
    actions: List[Action] = []
    state: List[str] = []

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([Reply])

