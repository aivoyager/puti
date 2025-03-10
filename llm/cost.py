"""
@Author: obstacles
@Time:  2025-03-10 17:10
@Description:  
"""
from pydantic import BaseModel
from constant.llm import TOKEN_COSTS


class Cost(BaseModel):
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_budget: float = 0
    max_budget: float = 10.0
    total_cost: float = 0
    token_costs: dict[str, dict[str, float]] = TOKEN_COSTS

    def update_cost(self, prompt_tokens, completion_tokens, model):
        """ Update cose """

