from puti.llm.tools import BaseTool, ToolArgs
from pydantic import Field
from typing import Annotated


class CalculatorArgs(ToolArgs):
    expression: str = Field(..., description="The mathematical expression to evaluate.")


class CalculatorTool(BaseTool):
    name: str = "Calculator"
    desc: str = "A tool to evaluate mathematical expressions."
    args: CalculatorArgs = None

    async def run(self, expression: str, *args, **kwargs) -> Annotated[str, 'tool result']:
        try:
            # WARNING: eval is not safe in a real production environment
            result = eval(expression, {"__builtins__": {}}, {})
            return f"The result of '{expression}' is {result}."
        except Exception as e:
            return f"Failed to evaluate expression: {e}" 