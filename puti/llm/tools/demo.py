"""
@Author: obstacles
@Time:  2025-03-17 17:21
@Description:  demo
"""
import json

from puti.llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field
from puti.llm.nodes import LLMNode, OpenAINode
from typing import Annotated


class GetFlightInfoArgs(ToolArgs):
    departure: str = Field(description='The departure city (airport code)')
    arrival: str = Field(description='The arrival city (airport code)')


class GetFlightInfo(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "get_flight_time"
    desc: str = 'Use this action get the flight times between two cities'
    args: GetFlightInfoArgs = None

    async def run(self, departure, arrival, *args, **kwargs):
        flights = {
            'NYC-LAX': {'departure': '08:00 AM', 'arrival': '11:30 AM', 'duration': '5h 30m'},
            'LAX-NYC': {'departure': '02:00 PM', 'arrival': '10:30 PM', 'duration': '5h 30m'},
            'LHR-JFK': {'departure': '10:00 AM', 'arrival': '01:00 PM', 'duration': '8h 00m'},
            'JFK-LHR': {'departure': '09:00 PM', 'arrival': '09:00 AM', 'duration': '7h 00m'},
            'CDG-DXB': {'departure': '11:00 AM', 'arrival': '08:00 PM', 'duration': '6h 00m'},
            'DXB-CDG': {'departure': '03:00 AM', 'arrival': '07:30 AM', 'duration': '7h 30m'},
        }
        key = f'{departure}-{arrival}'.upper()
        return json.dumps(flights.get(key, {'error': 'Flight not found'}))


class SearchResidentEvilInfoArgs(ToolArgs):
    name: str = Field(description='name in resident evil')


class SearchResidentEvilInfo(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "search_resident_evil_info"
    desc: str = "Use this action search the resident evil relation info"
    intermediate: bool = True
    args: SearchResidentEvilInfoArgs = None

    async def run(self, *args, **kwargs):
        llm: LLMNode = kwargs.get('llm')
        name = self.args.name
        resp = await llm.chat([{'role': 'user', 'content': f'请提供生化危机中这个角色的详细信息{name}'}])
        return resp
