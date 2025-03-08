"""
@Author: obstacles
@Time:  2025-03-04 14:08
@Description:  
"""

from llm.schema import Role, SystemMessage
from constant.llm import RoleType


class Developer(Role):
    name: str = 'obstacles'


class ALL(Role):
    name: str = '<all>'
    system_message: 'SystemMessage' = None
    identity: RoleType = ''
