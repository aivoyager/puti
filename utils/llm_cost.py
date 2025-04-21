"""
@Author: obstacles
@Time:  2025-04-18 18:03
@Description:  
"""
import tiktoken


def count_gpt_message_tokens(messages, model="gpt-4"):
    encoding = tiktoken.encoding_for_model('gpt-4')
    if model.startswith("gpt-4"):
        tokens_per_message = 3
        tokens_per_name = 1
    else:  # gpt-3.5 等
        tokens_per_message = 4
        tokens_per_name = -1  # Not applicable

    num_tokens = 0
    for msg in messages:
        num_tokens += tokens_per_message
        for key, value in msg.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # 每个 reply 的额外 token
    return num_tokens


def estimate_gpt_cost(prompt_tokens, completion_tokens, model="gpt-4"):
    if model == "gpt-4":
        prompt_cost = prompt_tokens / 1000 * 0.01
        completion_cost = completion_tokens / 1000 * 0.03
    elif "gpt-3.5" in model:
        prompt_cost = prompt_tokens / 1000 * 0.0005
        completion_cost = completion_tokens / 1000 * 0.0015
    else:
        prompt_cost = completion_cost = 0

    return {
        "total_tokens": prompt_tokens + completion_tokens,
        "total_cost": prompt_cost + completion_cost,
        "prompt_cost": prompt_cost,
        "completion_cost": completion_cost
    }
