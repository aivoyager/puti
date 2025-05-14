"""
@Author: obstacles
@Time:  2025-05-09 17:17
@Description:  
"""
from llm.roles import Role, RoleType, McpRole
from typing import List, Literal
from llm.tools.talk import Reply
from llm.tools.terminal import Terminal
from llm.tools.python import Python
from llm.tools.file import File


class Alex(Role):
    name: str = 'alex'

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_tools([Terminal, Python, File])
