"""
@Author: obstacles
@Time:  2025-03-26 15:36
@Description:  
"""
from llm.tools.demo import GetFlightInfo


def test_to_parameter():
    flight_info = GetFlightInfo()
    resp = flight_info.param
    a = resp['function']  # won't yellow highlighting
    assert resp
