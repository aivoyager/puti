"""
@Author: obstacles
@Time:  2025-03-27 14:15
@Description:  
"""
from llm.roles.tour_guide import TourGuide
from llm.nodes import ollama_node


def test_mcp_role():
    tour_guide = TourGuide(agent_node=ollama_node)
    text = '从纽约到洛杉矶的航班要持续多久'
    resp = tour_guide.cp.invoke(tour_guide.run, with_message=text)
    print('')
