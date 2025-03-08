"""
@Author: obstacles
@Time:  2025-03-07 14:41
@Description:  
"""
from llm.schema import Action
from llm.node import OpenAINode

class Talk(Action):
    name = 'Talk'
    node = OpenAINode(llm_name='openai')
    desc = ''

