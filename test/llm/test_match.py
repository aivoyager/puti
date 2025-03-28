"""
@Author: obstacles
@Time:  2025-03-21 14:22
@Description:  
"""
import re


def test_match():
    s = """
    
    test_function_calling.py::test_fc_in_env 
    
    ======================== 1 failed, 11 warnings in 7.35s ========================
    FAILED                          [100%]<think>
    Okay, so I'm trying to figure out how to respond to the user's message. The user asked, "从纽约（NYC）到洛杉矶（LAX）的航班要飞多长时间," which means they want to know the flight duration from NYC to LAX.
    
    Looking at the available tools, there's one called "Get flight time" that requires departure and arrival city codes. Since the user provided both cities with their airport codes (NYC for New York and LAX for Los Angeles), I can use this action.
    
    I don't need any intermediate steps because the information is straightforward, and I have all the necessary details to perform the "Get flight time" action directly. There's no mention of an intermediate action here, so I can proceed without delays.
    
    Now, based on the instructions, if I complete the "Get flight time" action, I should then use the "Reply" action to send the information back to the user. But in this case, since the goal is just to get the flight time and not search for other info or perform another task, I can proceed with the first step.
    
    Wait, no, the instructions say that after performing an intermediate action (like "Get flight time"), I might need to take another action based on its result. But here, getting the flight time is the main request, so after obtaining that information, I should immediately reply with it. So perhaps I can do both tools in sequence.
    
    But according to the system message, each user message needs a direct reply from me. So maybe I don't need an intermediate step and can directly get the flight time and then reply, but since they're separate tools, I might have to choose first the "Get flight time" action with the necessary arguments and then proceed to reply.
    
    Wait, but in this case, the user's question is only about the flight duration, so I don't need any intermediate steps. The next stage should be to get the flight time using the provided codes. So I'll set the state to 0 with departure as NYC and arrival as LAX.
    </think>
    
    {"state": 0, "arguments": {"departure": "NYC", "arrival": "LAX"}}
    """
    s2 = """
        So, my next possible tools are either to reply to the user's message or search for Resident Evil info. Since the user asked about flight time and I already provided a response via the intermediate step, the logical next move is to send that information back as a regular reply.

Therefore, the state should be 1, which is the "Reply" action, allowing me to communicate the flight duration clearly.
</think>

```json
{"state": 1}
```
    """
    pattern = r'\{"state":\s*\d+,\s*"arguments":\s*\{.*?\}\}'
    match = re.search(pattern, s, re.DOTALL)
    rs = match.group()

    p2 = r'\{"state":\s*\d+}'
    rs2 = re.search(p2, s2, re.DOTALL)

    import json
    rs = json.loads(rs)
    print('')
