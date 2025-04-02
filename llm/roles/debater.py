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
    goal: str = ('refute the opposing point at each turn. '
                 "You can't speak for the other debater."
                 'Pay attention to who your latest message record comes from, from the other side you need to directly refute him, if it is your own tool return, then sort out the appropriate result as the final output, your reply can only be related to the debate, do not add additional thinking information.')

