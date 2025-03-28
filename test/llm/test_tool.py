"""
@Author: obstacles
@Time:  2025-03-28 11:22
@Description:  
"""
from llm.tools.demo import GetFlightInfo
from llm.tools import toolkit


def test_base_tool_inherit():
    a = toolkit.add_tool(GetFlightInfo)
    b = toolkit.add_tools([GetFlightInfo])
    for name, tool in toolkit.toolkit.items():
        print(tool.param)

def test_tool_map():
    pass


