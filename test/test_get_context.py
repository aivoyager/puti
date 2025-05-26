"""
@Author: obstacles
@Time:  2025-04-25 17:18
@Description:  
"""
from puti.llm.nodes import OpenAINode

a = """
class Role(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='obstacles', description='role name')
    goal: str = ''
    skill: str = ''
    address: set[str] = Field(default=set(), description='', validate_default=True)
    toolkit: Toolkit = Field(default_factory=Toolkit, validate_default=True)
    identity: RoleType = Field(default=RoleType.ASSISTANT, description='Role identity')
    agent_node: LLMNode = Field(default_factory=OpenAINode, description='LLM node')
    rc: RoleContext = Field(default_factory=RoleContext)
    answer: Optional[Message] = Field(default=None, description='assistant answer')

    tool_calls_one_round: List[str] = Field(default=[], description='tool calls one round contains tool call id')

    cp: SerializeAsAny[Capture] = Field(default_factory=Capture, validate_default=True, description='Capture exception')
    faiss_db: SerializeAsAny[FaissIndex] = Field(
        default_factory=lambda: FaissIndex(
            from_file=str(root_dir() / 'data' / 'cz_filtered.json'),
            to_file=str(root_dir() / 'db' / 'cz_filtered.index')
        ),
        validate_default=True, description='faiss vector database')

    __hash__ = object.__hash__  # make sure hashable can be regarded as dict key

    @model_validator(mode='after')
    def check_address(self):
        if not self.address:
            self.address = {f'{any_to_str(self)}.{self.name}'}
        return self  # return self for avoiding warning

    @property
    def sys_think_msg(self) -> Optional[Dict[str, str]]:
        return {'role': RoleType.SYSTEM.val, 'content': self._env_prompt + self.role_definition}

    @property
    def sys_react_msg(self) -> Optional[Dict[str, str]]:
        return {'role': RoleType.SYSTEM.val, 'content': self.role_definition}

    @property
    def role_definition(self) -> str:
        name_exp = f'You name is {self.name}, an helpful AI assistant,'
        skill_exp = f'skill at {self.skill},' if self.skill else ''
        goal_exp = f'your goal is {self.goal}.' if self.goal else ''
        constraints_exp = (
            'You constraint is utilize the same language for seamless communication'
            ' and always give a clearly in final reply with format json format {"FINAL_ANSWER": Your final answer here}'
            ' do not give ANY other information except this json.'
            ' Pay attention to historical information to distinguish and make decision.'
       )
        tool_exp = (
            'You have some tools that you can use to help the user or meet user needs, '
            'fully understand the tool functions and their arguments before using them,'
            'make sure the types and values of the arguments you provided to the tool functions are correct'
            'and always provide parameters that must be worn, '
            'tools give you only the intermediate product, '
            'no matter whether use tool or not,'
            'ultimately you need to give a clearly final reply prefix with END like "END you final reply here",'
            'let others know that your part is done.'
            'If there is an error in calling the tool, you need to fix it yourself.'
        )
        finish_exp = ("Based on user requirements and your prior knowledge to jude "
                      "if you've accomplished your goal, prefix your final reply with 'END you reply'.")
        # definition = name_exp + skill_exp + goal_exp + constraints_exp + tool_exp
        definition = name_exp + skill_exp + goal_exp + constraints_exp
        return definition

    def publish_message(self):
        if not self.answer:
            return
        if self.answer and self.rc.env:
            self.rc.env.publish_message(self.answer)
            self.rc.memory.add_one(self.answer)  # this one won't be perceived
            self.answer = None

    def _reset(self):
        self.toolkit = Toolkit()

    def set_tools(self, tools: List[Type[BaseTool]]):
        self.toolkit.add_tools(tools)

    def _correction(self, fix_msg: str):
        lgr.debug("Self-Correction: %s", fix_msg)
        err = UserMessage(content=fix_msg, sender=RoleType.USER.val)
        self.rc.buffer.put_one_msg(err)
        return False, ''

    async def _perceive(self, ignore_history: bool = False) -> bool:
        news = self.rc.buffer.pop_all()
        history = [] if ignore_history else self.rc.memory.get()
        new_list = []
        for n in news:
            if n not in history:
                self.rc.memory.add_one(n)

            if (n.sender in self.rc.subscribe_sender
                    or self.address & n.receiver
                    or MessageRouter.ALL.val in n.receiver):
                if n not in history:
                    new_list.append(n)
        self.rc.news = new_list
        if len(self.rc.news) == 0:
            lgr.debug(f'{self} no new messages, waiting.')
        else:
            new_texts = [f'{m.role.val}: {m.content[:60]}...' for m in self.rc.news]
            lgr.debug(f'{self} perceive {new_texts}.')
        return True if len(self.rc.news) > 0 else False

    async def _think(self) -> Optional[Tuple[bool, str]]:
        message = [self.sys_think_msg] + Message.to_message_list(self.rc.memory.get())
        last_msg = message[-1]
        message_pure = []

        # only show tool call intermediate info when fc, history info won't process it
        if isinstance(last_msg, dict):
            my_prefix = f'{self.name}({self.identity.val}):'
            my_tool_prefix = f'{self.name}({RoleType.TOOL.val}):'
            if not last_msg['content'].startswith(my_prefix) and not last_msg['content'].startswith(my_tool_prefix):
                for msg in message:
                    if not isinstance(msg, dict):
                        if not isinstance(msg, ChatCompletionMessage):
                            message_pure.append(msg)
                            continue
                    else:
                        if not msg['content'].startswith(my_tool_prefix):
                            message_pure.append(msg)
                            continue
        message_pure = message if not message_pure else message_pure

        think: Union[ChatCompletionMessage, str] = await self.agent_node.chat(message_pure, tools=self.toolkit.param_list)

        # openai fc
        if isinstance(think, ChatCompletionMessage) and think.tool_calls:
            think.tool_calls = think.tool_calls[:1]
            todos = []
            for call_tool in think.tool_calls:
                todo = self.toolkit.tools.get(call_tool.function.name)
                todo_args = call_tool.function.arguments if call_tool.function.arguments else {}
                todo_args = json.loads(todo_args) if isinstance(todo_args, str) else todo_args
                tool_call_id = call_tool.id
                self.tool_calls_one_round.append(tool_call_id)  # a queue storage multiple calls and counter i
                todos.append((todo, todo_args, tool_call_id))

            # TODO: multiple tools call for openai support
            call_message = Message(non_standard=think)
            self.rc.memory.add_one(call_message)
            self.rc.todos = todos
            return True, ''
        # ollama fc
        elif isinstance(think, OMessage) and think.tool_calls and all(isinstance(i, OMessage.ToolCall) for i in think.tool_calls):
            tool_calls: List[OMessage.ToolCall] = think.tool_calls[:1]
            todos = []
            for fc in tool_calls:
                todo = self.toolkit.tools.get(fc.function.name)
                todo_args = fc.function.arguments if fc.function.arguments else {}
                todos.append((todo, todo_args, -1))

            call_message = Message(non_standard=think)
            self.rc.memory.add_one(call_message)
            self.rc.todos = todos
            return True, ''

        # from openai、ollama, different data structure.
        # llm reply directly
        elif (isinstance(think, ChatCompletionMessage) and think.content) or isinstance(think, str):  # think resp
            try:
                if isinstance(think, str):
                    content = json.loads(think)
                else:
                    content = json.loads(think.content)
                content = content.get('FINAL_ANSWER')
            except json.JSONDecodeError:
                # send to self, no publish, no action
                fix_msg = (f'Your returned an unexpected invalid json data, fix it please, '
                           f'make sure the repaired results include the full process and results rather than summary'
                           f'  ---> {think}')
                return self._correction(fix_msg)

            if content:
                json_match = re.search(r'({.*})', message_pure[-1]['content'], re.DOTALL)
                think_process = ''
                if json_match:
                    match_group = json_match.group()
                    if is_valid_json(match_group):
                        think_process = json.loads(match_group).get('think_process', '')
                self.answer = AssistantMessage(content=content, sender=self.name)
                return False, json.dumps({'final_answer': content, 'think_process': think_process})
            else:
                fix_msg = 'Your returned json data does not have a "FINAL ANSWER" key. Please check'
                return self._correction(fix_msg)

        # unexpected think format
        else:
            err = f'Unexpected chat response: {type(think)}'
            lgr.error(err)
            raise RuntimeError(err)

    async def _react(self) -> Optional[Message]:
        message = Message.from_any('no tools taken yet')
        for todo in self.rc.todos:
            run = partial(todo[0].run, llm=self.agent_node)
            try:
                resp = await run(**todo[1])
                resp = json.dumps(resp, ensure_ascii=False) if not isinstance(resp, str) else resp
            except Exception as e:
                message = Message(non_standard_dic={
                    'type': 'function_call_output',
                    'call_id': todo[2],
                    'output': str(e)
                })
                message = Message(content=str(e), sender=self.name, role=RoleType.TOOL, tool_call_id=todo[2])
            else:
                message = Message.from_any(resp, role=RoleType.TOOL, sender=self.name, tool_call_id=todo[2])
            finally:
                self.rc.buffer.put_one_msg(message)
                self.rc.action_taken += 1
                self.answer = message
        return message

    async def run(self, with_message: Optional[Union[str, Dict, Message]] = None, ignore_history: bool = False) -> Optional[Message]:
        if with_message:
            msg = Message.from_any(with_message)
            self.rc.buffer.put_one_msg(msg)

        self.rc.action_taken = 0
        resp = Message(content='No action taken yet', role=RoleType.SYSTEM)
        while self.rc.action_taken < self.rc.max_react_loop:
            perceive = await self._perceive()
            if not perceive:
                self.publish_message()
                break
            todo, reply = await self._think()
            if not todo:
                self.publish_message()
                return reply
            resp = await self._react()
        self.rc.todos = []
        return resp
"""


def test_get_context():
    import os

    EXCLUDED_DIRS = {'data', 'logs', 'test', 'core', 'docs', 'conf', 'constant', 'db', 'prompts', 'run',
                     'supervisor.d', 'utils'}
    EXCLUDED_FILES = ['README.md', 'pytest.ini', 'requirements.txt',
                      '.gitignore', '.env', '__pycache__', 'Dockerfile', 'docker-compose.yml', 'docker_run.sh',
                      'setup.py', 'logs_uvicore.py', 'LICENSE', 'a']

    def should_skip_dir(dirname):
        return (
                dirname.startswith('.') or
                dirname in EXCLUDED_DIRS
        )

    def collect_file_contexts(root_path: str, output_txt_path: str, target_subdir: str = None):  # <-- 添加参数
        file_contexts = []

        for dirpath, dirnames, filenames in os.walk(root_path):
            # 只处理指定的子目录（如果指定了）
            if target_subdir:
                rel_path = os.path.relpath(dirpath, root_path)
                if not rel_path.startswith(target_subdir):
                    continue

            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if filename in EXCLUDED_FILES:
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    print(f"跳过无法读取的文件: {file_path}，错误：{e}")
                    continue

                rel_dir = os.path.relpath(dirpath, root_path)
                if rel_dir == ".":
                    module_path = filename
                else:
                    module_path = f"{rel_dir.replace(os.sep, '.')}.{filename}"

                entry = (
                    "*****************************************************\n"
                    f"`{module_path}` `{filename}`\n\n"
                    f"{content}\n"
                )
                file_contexts.append(entry)

        full_text = "\n".join(file_contexts)

        with open(output_txt_path, 'w', encoding='utf-8') as f_out:
            f_out.write(full_text)

        print(f"已保存所有上下文到：{output_txt_path}")

    # ✅ 使用时只读取 puti/agent 目录
    # collect_file_contexts(
    #     root_path="/Users/wangshuang/PycharmProjects/puti/puti",
    #     output_txt_path="/Users/wangshuang/PycharmProjects/puti/puti/data/agent_context.txt",
    #     target_subdir="agent"  # ✅ 只抓取 agent 目录
    # )

    collect_file_contexts(
        root_path="/Users/wangshuang/PycharmProjects/puti/puti",
        output_txt_path="/Users/wangshuang/PycharmProjects/puti/puti/data/llm.txt",
        target_subdir="llm"
    )


def test_gen_docs():
    prompt = """
你将阅读的是一个项目的部分模块的全部代码上下文内容，格式为：

*****************************************************
`模块路径.文件名` `文件名`

文件内容
*****************************************************
`模块路径.文件名` `文件名`

另一个文件内容
...

下面为这个模块的所有文件上下文：
{context}


你的任务是根据这个模块项目代码上下文，这不是metagpt！，生成一份该模块的介绍，输出为 Markdown 格式，要求如下：
1. 项目介绍总字数不要超过 1000 字符！；
2. 重点突出项目的 **架构设计**，包括模块划分、职责分离、调用关系等；
3. 详细说明项目中的 **multi-agent 协作机制**（如有 agent 的定义、注册、调度、任务协作等）；
5. 尽量结合具体代码结构、类名、方法名等内容进行讲解；
6. 使用 Markdown 格式输出，内容清晰、分层合理、有标题小节；
7. 不要复制原始代码内容，但可以引用重要的类名、方法名、结构名称来辅助说明。
8. 根据上面的上下文来，不要编造任何内容

请开始生成项目介绍。
    """
    """4. 深入描述 **MCP（Multi-agent Communication Protocol）** 通信机制的实现方式与使用流程；"""
    with open('/Users/wangshuang/PycharmProjects/puti/puti/data/llm.txt', 'r') as f:
        context = f.read()
    prompt.format(context=context)
    n = OpenAINode()
    import asyncio

    resp = asyncio.run(n.chat([{'role': 'user', 'content': prompt}]))
    print(resp)

    print('')
    with open('/Users/wangshuang/PycharmProjects/puti/puti/data/llm.md', 'w') as f:
        f.write(resp)
    print('')

