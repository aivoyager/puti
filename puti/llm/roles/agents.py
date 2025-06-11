"""
@Author: obstacles
@Time:  2025-06-04 11:30
@Description:  
"""
from typing import Any
from puti.llm.roles import McpRole
from puti.llm.messages import UserMessage
from puti.logs import logger_factory
from puti.llm.prompts import PromptSetting
from puti.llm.roles import Role
from puti.llm.tools.web_search import WebSearch
from puti.llm.tools.project_analyzer import ProjectAnalyzer
from puti.llm.tools.terminal import Terminal
from puti.llm.tools.python import Python
from puti.llm.tools.file import File


lgr = logger_factory.llm

__all__ = ['Alex', 'CZ', 'Debater']


class Alex(Role):
    name: str = 'alex'

    def model_post_init(self, __context: Any) -> None:
        self.set_tools([WebSearch, Terminal, ProjectAnalyzer, Python, File])


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
            prompt = PromptSetting.rag_template.format(his_rsp, text)
            resp = await super(CZ, self).run(prompt, *args, **kwargs)
        return resp


class Debater(Role):
    name: str = '乔治'

    def model_post_init(self, __context: Any) -> None:
        self.set_tools([WebSearch])
