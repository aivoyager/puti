"""
@Author: obstacles
@Time:  2025-03-04 14:08
@Description:  
"""
from llm.prompts import prompt_setting
from llm.actions import Action
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from typing import Optional, List, Iterable, Literal
from constant.llm import RoleType
from logs import logger_factory
from typing import Dict, Tuple, Type, Any, Union
from constant.llm import TOKEN_COSTS, MessageRouter
from asyncio import Queue, QueueEmpty
from llm.nodes import LLMNode, OpenAINode
from llm.messages import Message
from llm.envs import Env
from llm.memory import Memory

lgr = logger_factory.llm


class Buffer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _queue: Queue = PrivateAttr(default_factory=Queue)

    def put_one_msg(self, msg: Message):
        self._queue.put_nowait(msg)

    def pop_one(self) -> Optional[Message]:
        try:
            item = self._queue.get_nowait()
            if item:
                # indicate that task already done
                self._queue.task_done()
            return item
        except QueueEmpty:
            return None

    def pop_all(self) -> List[Message]:
        resp = []
        while True:
            msg = self.pop_one()
            if not msg:
                break
            resp.append(msg)
        return resp


class RoleContext(BaseModel):
    env: Env = Field(default=None)
    buffer: Buffer = Field(default_factory=Buffer, exclude=True)
    memory: Memory = Field(default_factory=Memory)
    news: List[Message] = Field(default=None, description='New messages need to be handled')
    subscribe_sender: set[str] = Field(default={}, description='Subscribe role name for solution-subscription mechanism')
    interested_action: set[str] = Field(default={}, description='Interested action')
    max_react_loop: int = Field(default=5, description='Max react loop number')
    state: int = Field(default=-1, description='State of the action')
    todo: Action = Field(default=None, exclude=True, description='Action to do')


class Role(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='obstacles', description='role name')
    sex: Literal['male', 'female'] = 'male'
    age: int = ''
    job: str = ''
    skill: str = ''
    goal: str = ''
    personality: str = ''
    constraints: str = Field(
        default='utilize the same language as the user requirements for seamless communication',
        validate_default=True
    )
    address: set[str] = Field(default=set(), description='')

    system_message: str = Field(default='You are a helpful assistant.', description='System message')
    actions: List[Action] = Field(default=[], validate_default=True, description='Action list can be performed')
    states: List[str] = Field(default=[], validate_default=True, description='Action to state number map')
    identity: RoleType = Field(default=RoleType.USER, description='Role identity')
    agent_node: LLMNode = Field(default_factory=OpenAINode, description='LLM node')
    rc: RoleContext = Field(default_factory=RoleContext)

    @property
    def role_definition(self) -> str:
        name_exp = f'You name is {self.name}.' if self.name else ''
        sex_exp = f'You sex is {self.sex}.' if self.sex else ''
        age_exp = f'You age is {self.age}.' if self.age else ''
        job_exp = f'You job is {self.job}.' if self.job else ''
        skill_exp = f'You skill at {self.skill}.' if self.skill else ''
        goal_exp = f'You goal is {self.goal}.' if self.goal else ''
        personality_exp = f'You personality is {self.personality}.' if self.personality else ''
        constraints_exp = f'You constraints are {self.constraints}.' if self.constraints else ''
        definition = name_exp + sex_exp + age_exp + job_exp + skill_exp + goal_exp + personality_exp + constraints_exp
        return definition

    def _reset(self):
        self.states = []
        self.actions = []

    def set_actions(self, actions: List[Union[Action, Type[Action]]]):
        for action in actions:
            act_obj = action()
            self.actions.append(act_obj)
            self.states.append(f'{len(self.actions) - 1}. {action}, action name: {act_obj.name}, action description: {act_obj.desc}\n')

    async def run(self, with_message: Optional[Union[str, Dict, Message]] = None, ignore_history: bool = False) -> Optional[Message]:
        if with_message:
            msg = None
            if isinstance(with_message, str):
                msg = Message(content=with_message)
            elif isinstance(with_message, Message):
                msg = with_message
            elif isinstance(with_message, Dict):
                u_name = next(iter(with_message.keys()))
                if u_name not in RoleType.keys():
                    raise KeyError('Unknown role: {}'.format(u_name))
                with_message = next(iter(with_message.values()))
                msg = Message(content=with_message, sender=u_name)
            else:
                raise TypeError('with_message must be str or dict or `Message`')
        self.rc.buffer.put_one_msg(msg)

        news = self.rc.buffer.pop_all()
        history = [] if ignore_history else self.rc.memory.get()
        self.rc.memory.add_batch(news)
        self.rc.news = [n for n in news if (n.sender in self.rc.subscribe_sender or self.name in n.receiver or n.receiver == MessageRouter.ALL.val) and n not in history]
        if not len(self.rc.news):
            lgr.debug(f'{self.name}:{self.identity.val} no new messages, waiting.')
        else:
            new_texts = [f'{m.role}: {m.content[:20]}' for m in self.rc.news]
            lgr.debug(f'{self.name}:{self.identity.val} observe {new_texts}.')

        actions_taken = 0
        while actions_taken < self.rc.max_react_loop:
            # if len(self.actions) == 1:
            #     self.rc.state = 0
            #     to_do = self.actions[self.rc.state] if self.rc.state >= 0 else None
            # else:
            prompt = prompt_setting.COMMON_STATE_TEMPLATE.format(
                history=self.rc.memory.get(),
                states='\n'.join(self.states),
                n_states=len(self.states) - 1,
                previous_state=self.rc.state
            )
            sys_msg = {'role': RoleType.SYSTEM.val, 'content': self.role_definition}
            message = {'role': self.identity.val, 'content': prompt}
            choose = await self.agent_node.achat([sys_msg, message])
            print('')

    async def _get_corporate_prompt(self):
        prompt = ''
        if self.rc.env and self.rc.env.desc:
            all_roles = self.rc.env.members.keys()
            other_roles = ', '.join([r for r in all_roles if r != self.name])
            env_desc = f'You are in {self.rc.env.desc} with roles({other_roles})'
            prompt += env_desc
        return prompt
