
"""
@Author: obstacle
@Time: 21/01/25 18:15
@Description:  
"""
from pydantic_settings import BaseSettings


class PromptSettings(BaseSettings):
    preprocess_model: dict = {
        "default": (
            "你只要回复0 和 1 ，代表不需要使用工具。以下几种问题不需要使用工具:\n"
            "1. 需要联网查询的内容\n"
            "2. 需要计算的内容\n"
            "3. 需要查询实时性的内容\n"
            "如果我的输入满足这几种情况，返回1。其他输入，请你回复0，你只要返回一个数字\n"
            "这是我的问题:"
        ),
    }
    llm_model: dict = {
        "default": "{{input}}",
        "gpt-4o-mini": (
            "You are a versatile AI assistant. Depending on the user's input, perform the following tasks:\n"
            "- If the input is a question, answer it concisely.\n"
            "- If the input requires summarization, provide a short and accurate summary.\n"
            "- If the input is a request for code, generate the code snippet with comments.\n\n"
            "User input:\n"
            "{{input}}\n\n"
            "Your response:"
        ),
        "with_history": (
            "The following is a friendly conversation between a human and an AI.\n"
            "The AI is talkative and provides lots of specific details from its context.\n"
            "If the AI does not know the answer to a question, it truthfully says it does not know.\n\n"
            "Current conversation:\n"
            "{{history}}\n"
            "Human: {{input}}\n"
            "AI:"
        ),
    }
    action_model: dict = {
        "GPT-4": (
            "Answer the following questions as best you can. You have access to the following tools:\n"
            "The way you use the tools is by specifying a json blob.\n"
            "Specifically, this json should have a `action` key (with the name of the tool to use) and a `action_input` key (with the input to the tool going here).\n"
            'The only values that should be in the "action" field are: {tool_names}\n'
            "The $JSON_BLOB should only contain a SINGLE action, do NOT return a list of multiple actions. Here is an example of a valid $JSON_BLOB:\n"
            "```\n\n"
            "{{{{\n"
            '  "action": $TOOL_NAME,\n'
            '  "action_input": $INPUT\n'
            "}}}}\n"
            "```\n\n"
            "ALWAYS use the following format:\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action:\n"
            "```\n\n"
            "$JSON_BLOB"
            "```\n\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n"
            "Begin! Reminder to always use the exact characters `Final Answer` when responding.\n"
            "Question:{input}\n"
            "Thought:{agent_scratchpad}\n"
        ),
        "ChatGLM3": (
            "You can answer using the tools.Respond to the human as helpfully and accurately as possible.\n"
            "You have access to the following tools:\n"
            "{tools}\n"
            "Use a json blob to specify a tool by providing an action key (tool name)\n"
            "and an action_input key (tool input).\n"
            'Valid "action" values: "Final Answer" or  [{tool_names}]\n'
            "Provide only ONE action per $JSON_BLOB, as shown:\n\n"
            "```\n"
            "{{{{\n"
            '  "action": $TOOL_NAME,\n'
            '  "action_input": $INPUT\n'
            "}}}}\n"
            "```\n\n"
            "Follow this format:\n\n"
            "Question: input question to answer\n"
            "Thought: consider previous and subsequent steps\n"
            "Action:\n"
            "```\n"
            "$JSON_BLOB\n"
            "```\n"
            "Observation: action result\n"
            "... (repeat Thought/Action/Observation N times)\n"
            "Thought: I know what to respond\n"
            "Action:\n"
            "```\n"
            "{{{{\n"
            '  "action": "Final Answer",\n'
            '  "action_input": "Final response to human"\n'
            "}}}}\n"
            "Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary.\n"
            "Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation:.\n"
            "Question: {input}\n\n"
            "{agent_scratchpad}\n"
        ),
        "structured-chat-agent": (
            "Respond to the human as helpfully and accurately as possible. You have access to the following tools:\n\n"
            "{tools}\n\n"
            "Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).\n\n"
            'Valid "action" values: "Final Answer" or {tool_names}\n\n'
            "Provide only ONE action per $JSON_BLOB, as shown:\n\n"
            '```\n{{\n  "action": $TOOL_NAME,\n  "action_input": $INPUT\n}}\n```\n\n'
            "Follow this format:\n\n"
            "Question: input question to answer\n"
            "Thought: consider previous and subsequent steps\n"
            "Action:\n```\n$JSON_BLOB\n```\n"
            "Observation: action result\n"
            "... (repeat Thought/Action/Observation N times)\n"
            "Thought: I know what to respond\n"
            'Action:\n```\n{{\n  "action": "Final Answer",\n  "action_input": "Final response to human"\n}}\n\n'
            "Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation\n"
            "{input}\n\n"
            "{agent_scratchpad}\n\n"
            # '(reminder to respond in a JSON blob no matter what)')
        ),
    }
    postprocess_model: dict = {
        "default": "{{input}}",
    }


prompt_settings = PromptSettings()
