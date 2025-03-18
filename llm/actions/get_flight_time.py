"""
@Author: obstacles
@Time:  2025-03-17 17:21
@Description:  demo
"""
import json

from llm.actions import Action, ActionArgs
from pydantic import ConfigDict, Field
from llm.nodes import LLMNode, OpenAINode
from typing import Annotated


class GetFlightInfoArgs(ActionArgs):
    departure: str = Field(description='The departure city (airport code)')
    arrival: str = Field(description='The arrival city (airport code)')


class GetFlightInfo(Action):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "Get flight time"
    desc: str = 'Use this action get the flight times between two cities'
    args: GetFlightInfoArgs = None

    async def run(self, *args, **kwargs):
        departure = self.args.departure
        arrival = self.args.arrival
        flights = {
            'NYC-LAX': {'departure': '08:00 AM', 'arrival': '11:30 AM', 'duration': '5h 30m'},
            'LAX-NYC': {'departure': '02:00 PM', 'arrival': '10:30 PM', 'duration': '5h 30m'},
            'LHR-JFK': {'departure': '10:00 AM', 'arrival': '01:00 PM', 'duration': '8h 00m'},
            'JFK-LHR': {'departure': '09:00 PM', 'arrival': '09:00 AM', 'duration': '7h 00m'},
            'CDG-DXB': {'departure': '11:00 AM', 'arrival': '08:00 PM', 'duration': '6h 00m'},
            'DXB-CDG': {'departure': '03:00 AM', 'arrival': '07:30 AM', 'duration': '7h 30m'},
        }
        # 将出发地和目的地组合成键，并查找航班信息
        key = f'{departure}-{arrival}'.upper()
        return json.dumps(flights.get(key, {'error': 'Flight not found'}))
