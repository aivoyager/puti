"""
@Author: obstacles
@Time:  2025-03-06 17:52
@Description:  
"""
from constant.llm import RoleType


def test_get_enum_member():
    RoleType.elem_from_str('user')
