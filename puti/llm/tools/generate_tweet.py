"""
@Author: obstacles
@Time:  2025-04-09 16:35
@Description:  
"""
import json
import re
import asyncio

from puti.utils.path import root_dir
from abc import ABC
from puti.llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field
from puti.llm.nodes import OllamaNode, LLMNode
from puti.conf.llm_config import LlamaConfig, OpenaiConfig
from puti.llm.nodes import OpenAINode
from logs import logger_factory
from puti.constant.llm import RoleType
from puti.llm.messages import Message, SystemMessage, UserMessage

lgr = logger_factory.llm
model = 'gemini-2.5-pro-preview-03-25'


class GenerateCzArgs(ToolArgs):
    topic: str = Field(
        default='',
        description="""`topic` is an optional parameter that guides tweet generation toward a specific theme, subject, or keyword.
If the user’s input clearly expresses a desire to focus on a particular topic (e.g., “Write a tweet about Elon Musk”), extract the relevant keyword or phrase and set it as the topic.
If the input is vague or does not suggest any particular direction (e.g., “Post something funny”), leave topic unset and allow the model to generate freely.
"""
)


class GenerateCzTweet(BaseTool, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'generate_tweet'
    desc: str = 'Use this tool to generate a cz tweet can be posted on x website.'
    args: GenerateCzArgs = None

    async def run(self, topic='', *args, **kwargs):
        conf = OpenaiConfig(MODEL=model)
        gemini = OpenAINode(conf=conf)
        topic_exp = f' related to topic: "{topic}"'
        topic_constraint = (f'Express some of my own opinions on this topic, '
                            f'Make sure you fully understand the relevant concepts of this topic, '
                            f'Ensure the logic and rationality of the tweets you post about this topic.')
        if not topic:
            topic_exp = ''
            topic_constraint = ''
        sys = """
You play a role in the blockchain area called "赵长鹏" （cz or changpeng zhao）, Reply with his accent.
"""
        prompt = f"""
1. Come up a tweet{topic_exp}, which tweet characters must be around 200. 
2. Just give the tweet and think process, nothing extra.
3. Easier to understand(English).{topic_constraint} Be more diverse and don't always use fixed catchphrases.
4. Your cognition is limited. For some unfamiliar fields, reply to tweets like a normal person. Sometimes casually, sometimes seriously. 
5. Don't act too much like an expert.Analyze cz's recent 30 tweet style (Retweets are not counted) from your search results.
Return in fixed json format:
"""
        json_format = ' {"generated_tweet": Your generated tweet result, "think_process": Your think process result}'
        prompt += json_format

        with open(root_dir() / 'data' / 'tweet_chunk.txt', 'r') as f:
            his_tweets = f.read()
        history_tweets_prompt = (
            f'\nThe following are some historical tweets of cz that are separated by the'
            f' === symbol as style references\n{his_tweets}'
        )
        prompt += history_tweets_prompt

        message = [
            SystemMessage(sys).to_message_dict(),
            UserMessage(prompt).to_message_dict(),
        ]
        resp = await gemini.chat(message)
        plain_resp = resp.lstrip('```json').rstrip('```').strip()
        json_resp = json.loads(plain_resp)
        return json_resp

    async def run_r1_14b(self, topic='', *args, **kwargs):
        llm: LLMNode = kwargs.get('llm')
        prompt = """
Below are instructions that describe the task, along with input that provides more context.
Write a response that completes the request appropriately.
Before answering, think carefully about the question and create a step-by-step thought chain to ensure that the answer is logical and accurate.

### Instruction
You play a role in the blockchain area called "赵长鹏" （cz or changpeng zhao）. Reply with his accent, 
speak in his habit. He goes by the Twitter name CZ �� BNB or cz_binance or 大表哥 and is commonly known as cz. 

### Question
User: {}

### Response
Assistant: <think>{}
        """
        topic_exp = f'must related to topic: "{topic}"'
        if topic:
            user_input = f'Come up a tweet as cz {topic_exp}, which tweet characters must between 150 and 200.'
        else:
            user_input = f'Come up a tweet as cz, which tweet characters must between 50 and 240.'
        prompt = prompt.format(user_input, '')
        # ds r1 not recommend system message
        conversation = [{'role': 'user', 'content': prompt}]
        conf = LlamaConfig()
        conf.MODEL = 'cz_14b:tweet'
        node = OllamaNode(llm_name='cz', conf=conf)
        resp = await node.chat(conversation)
        while self.validate_resp(resp, llm)[0] is False:
            lgr.warning(self.validate_resp(resp, llm)[1])
            resp = await node.chat(conversation)
        final_rs = self.validate_resp(resp, llm)[1]
        if final_rs.endswith(','):
            final_rs = final_rs.rstrip(',') + '.'
        return {'generated_tweet': final_rs}

    @staticmethod
    def validate_by_llm(text, llm):
        msg = [{'role': 'system', 'content': 'As a moderator of the content of tweets.'},
               {'role': 'user', 'content': 'Judging from the content whether this is a reasonable tweet, '
                                           'the logic is normal, the English and Chinese expression is normal '
                                           '(full text in Chinese or English), not because of the model illusion'
                                           ' generated by gibberish. And The content of the tweet must be consistent '
                                           'with what Zhao Changpeng (cz、赵长鹏) might post otherwise it is'
                                           'not normal. If normal, '
                                           'only "1" is returned, if abnormal, '
                                           f'only "0" is returned.\n tweet: {text}'}]
        loop = asyncio.get_event_loop()
        resp = loop.run_until_complete(llm.chat(msg))
        if resp == '1':
            return True
        else:
            return False

    def validate_resp(self, text, llm):
        match = re.search(r'</think>(.*)', text) or re.search(r'(?<=Assistant:\s)(.*)', text, re.DOTALL)
        if match:
            length = len(match.group(1).strip())
            if length > 240 or length < 50:
                return False, f'Generate tweet len is invalid. origin: {text}'
            if self.validate_by_llm(text, llm) is False:
                return False, f'llm think its invalid. origin: {text}'
            return True, match.group(1).strip()
        else:
            has_think = bool(re.search(r'<think>', text))
            has_think_end = bool(re.search(r'</think>', text))
            if not has_think and not has_think_end:
                if len(text.strip()) > 270 or len(text.strip()) < 50:
                    return False, f'Generate tweet len is invalid. origin: {text}'
                if self.validate_by_llm(text, llm) is False:
                    return False, f'llm think its invalid. origin: {text}'
                return True, text.strip()
            return False, f'The </think> tag is missing in the text. origin: {text}'
