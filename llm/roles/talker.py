"""
@Author: obstacles
@Time:  2025-03-07 14:10
@Description:  
"""
from llm.roles import Role, RoleType, McpRole
from typing import List, Literal
from llm.tools.talk import Reply
from llm.tools import BaseTool
from llm.tools.demo import GetFlightInfoArgs, GetFlightInfo, SearchResidentEvilInfo


class PuTi(Role):
    name: str = 'puti'

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_tools([GetFlightInfo, Reply])


class PuTiMCP(McpRole):
    """ use tools from mcp server """
    name: str = 'puti-mcp'
