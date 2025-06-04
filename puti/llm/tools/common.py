"""
@Author: obstacles
@Time:  2025-04-11 13:53
@Description:  
"""

from puti.llm.tools import BaseTool
from datetime import date


class GetTodayDate(BaseTool):
    name: str = 'get_today_date'
    desc: str = 'use this tool get today date'

    def run(self, *args, **kwargs) -> dict:
        now = str(date.today())
        return {'today': now}
