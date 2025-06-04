"""
@Author: obstacle
@Time: 21/01/25 11:46
@Description:  
"""
from pydantic_settings import BaseSettings
from pydantic import BaseModel


class PromptSetting(BaseSettings):
    rag_template: str = """"
Here is some reference information that you can use to answer the user's question:

### Reference Information:
{}

### User's Question:
{}

### Your Answer:
Based on the above provided information (Just a reference.), please answer the user's question.
 Ensure that your answer is comprehensive, directly related, and uses the reference information to form a well-supported response. 
 There is no need to mention the content you referred to in the reply.
    """

    THINK_TEMPLATE: str = """
Conversation History
===
{history}
===
Your previous choose : {previous_state}, based on conversation history choose one of the following stages you need to go in the next step.
No matter what, only return fixed JSON format(all double quotes) {"state": a number between -1 ~ {n_states}, "arguments": {argument name if action have arguments else leave an empty: argument value}}, don't reply anything else.
You have the following tools to choose from, please fully understand these tools and its arguments, select the most appropriate action state.
～～～
-1. Based on extra demands in system message if you have, if you think you have completed your goal, return {"state": -1, "arguments": {}} directly
{states}
～～～
Notes: 
1. You are forbidden to choose {previous_state} stage
2. If you already think you complete your goal and get the final answer through previous intermediate action, return {"state": -1, "arguments": {"message": you final answer}}
"""


prompt_setting = PromptSetting()
