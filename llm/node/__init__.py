"""
@Author: obstacles
@Time:  2025-03-07 11:01
@Description:  
"""

from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.types import CompletionUsage
from logs import logger_factory
from typing import List, Dict
from llm.schema import LLMNode

lgr = logger_factory.llm


class OpenAINode(LLMNode):

    async def achat(self, messages: List[Dict], stream=True) -> str:
        resp: AsyncStream[ChatCompletionChunk] = await self.acli.chat.completions.create(
            messages=messages,
            timeout=self.conf.LLM_API_TIMEOUT,
            stream=self.conf.STREAM,
            max_tokens=self.conf.MAX_TOKEN,
            temperature=self.conf.TEMPERATURE,
            model=self.conf.MODEL

        )
        collected_messages = []
        async for chunk in resp:
            chunk_message = chunk.choices[0].delta.content or '' if chunk.choices else ''
            finish_reason = (chunk.choices[0].finish_reason if chunk.choices and hasattr(chunk.choices[0], 'finish_reason') else None)
            chunk_has_usage = hasattr(chunk, 'usage') and chunk.usage
            # TODO: get chunk usage
            if finish_reason:
                if chunk_has_usage:
                    usage = chunk.usage
                elif hasattr(chunk.choices[0], 'usage'):
                    usage = CompletionUsage(**chunk.choices[0].usage)
                print('\n')
            print(chunk_message, end='')
            collected_messages.append(chunk_message)
        full_reply = ''.join(collected_messages)
        return full_reply
