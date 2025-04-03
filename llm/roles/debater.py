"""
@Author: obstacles
@Time:  2025-03-13 11:05
@Description:  
"""
from llm.tools.talk import Reply
from llm.roles.talker import PuTi, McpRole
from llm.tools.debate import Debate
from llm.envs import Env
from llm.roles.talker import PuTi, PuTiMCP
from llm.messages import Message
from llm.nodes import OllamaNode, ollama_node


class Debater(McpRole):
    name: str = '乔治'
    skill: str = 'debate contest'

