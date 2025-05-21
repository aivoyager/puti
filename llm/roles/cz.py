"""
@Author: obstacles
@Time:  2025-04-09 16:32
@Description:  
"""
from typing import Any

from llm.roles import McpRole
from llm.tools.generate_tweet import GenerateTweet
from llm.messages import UserMessage
from db.faisss import FaissIndex
from utils.path import root_dir
from logs import logger_factory

lgr = logger_factory.llm

rag_prompt = """
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


class CZ(McpRole):
    name: str = 'cz or 赵长鹏 or changpeng zhao'

    def model_post_init(self, __context: Any) -> None:
        self.agent_node.conf.MODEL = 'gemini-2.5-pro-preview-03-25'

    async def run(self, text, *args, **kwargs):
        self.agent_node.conf.STREAM = False
        intention_prompt = """
        Determine the user's intention, whether they want to post or receive a tweet. 
        Only return 1 or 0. 1 indicates that the user wants you to give them a tweet; otherwise, it is 0.
        Here is user input: {}
        """.format(text)
        judge_rsp = await self.agent_node.chat([UserMessage.from_any(intention_prompt).to_message_dict()])
        lgr.debug(f'post tweet choice is {judge_rsp}')
        if judge_rsp == '1':
            resp = await super(CZ, self).run(text, *args, **kwargs)
        else:
            search_rsp = self.faiss_db.search(text)[1]
            numbered_rsp = []
            for i, j in enumerate(search_rsp, start=1):
                numbered_rsp.append(f'{i}. {j}')
            his_rsp = '\n'.join(numbered_rsp)
            prompt = rag_prompt.format(his_rsp, text)
            resp = await super(CZ, self).run(prompt, *args, **kwargs)
        return resp
