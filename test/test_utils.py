"""
@Author: obstacles
@Time:  2025-04-01 14:22
@Description:  
"""
from puti.utils.common import tool_args_to_fc_schema
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Annotated
from puti.llm.tools.debate import DebateArgs


def test_pydantic_to_fc_calling():
    class InnerModel(BaseModel):
        inner_str: str = "hello"
        inner_int: int = 42

    class ExampleArgs(BaseModel):
        name: str = "alex"
        age: int = 25
        active: bool = True
        scores: List[int] = [90, 85, 88]
        metadata: Dict[str, Any] = {"key": "value"}
        details: InnerModel = InnerModel()

    class WeatherArgs(BaseModel):
        location: Annotated[str, "The city and state, e.g. San Francisco, CA"] = Field()
        # unit: Annotated[str, ["celsius", "fahrenheit"]] = Field()

    # e = ExampleArgs()
    # d = DebateArgs()
    fc_json = tool_args_to_fc_schema(ExampleArgs)
    fc_json2 = tool_args_to_fc_schema(DebateArgs)
    print(fc_json)
