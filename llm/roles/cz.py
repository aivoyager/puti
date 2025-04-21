"""
@Author: obstacles
@Time:  2025-04-09 16:32
@Description:  
"""

from llm.roles import McpRole
from llm.tools.generate_tweet import GenerateTweet


class CZ(McpRole):
    name: str = 'cz or 赵长鹏 or changpeng zhao'
