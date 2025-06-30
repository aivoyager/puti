"""
@Author: obstacles
@Time:  2025-03-10 17:10
@Description:  
"""
import tiktoken

from typing import List
from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel
from puti.constant.llm import TOKEN_COSTS


class CostManager(BaseModel):
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_budget: float = 0
    total_cost: float = 0
    token_costs: dict[str, dict[str, float]] = TOKEN_COSTS

    def update_cost(self, prompt_tokens, completion_tokens, model):
        """Update consumption and cost."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        price = self.token_costs.get(model, self.token_costs.get("gpt-3.5-turbo"))
        input_cost = prompt_tokens / 1000 * price["prompt"]
        output_cost = completion_tokens / 1000 * price["completion"]
        cost = round(input_cost + output_cost, 8)
        self.total_cost += cost
        self.total_budget += cost
        return cost

    @staticmethod
    def count_gpt_message_tokens(messages: List[dict], model: str) -> int:
        """Accurately calculate the number of tokens in a message."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        tokens_per_message = 3  # Each message consumes an additional 3 tokens for role, content, delimiter
        return sum(
            len(encoding.encode(m['content'])) if not m['content'] is None else 0 + tokens_per_message
            for m in messages if not isinstance(m, ChatCompletionMessage)
        )

    def estimate_gpt_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Accurately estimate the cost of a GPT model."""
        price = self.token_costs.get(model, self.token_costs["gpt-3.5-turbo"])
        return round((prompt_tokens * price["prompt"] + completion_tokens * price["completion"]) / 1000, 8)

    def handle_chat_cost(self, msg, reply, model):
        """Handle the tokens and cost of a chat."""
        prompt_tokens = self.count_gpt_message_tokens(msg, model)
        completion_tokens = self.count_gpt_message_tokens([{'content': reply}], model)
        cost = self.estimate_gpt_cost(prompt_tokens, completion_tokens, model)
        self.update_cost(prompt_tokens, completion_tokens, model)
        return cost

