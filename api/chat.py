"""
@Author: obstacles
@Time:  2025-04-09 16:25
@Description:  
"""
import asyncio

from typing import Optional
from fastapi import APIRouter, Request
from api import GetTweetsByNameRequest
from llm.roles.cz import CZ
from core.resp import Response
from pydantic import BaseModel, Field
from llm.nodes import OpenAINode
from llm.messages import UserMessage


chat_router = APIRouter()


class GenerateCzTweetRequest(BaseModel):
    text: Optional[str] = ''


class AskLlmRequest(BaseModel):
    model_name: Optional[str] = Field(default='gemini-2.5-pro-preview-03-25', description='model name')
    text: str


@chat_router.post('/generate_cz_tweet')
def generate_cz_tweet(request: GenerateCzTweetRequest):
    cz = CZ()
    resp = cz.cp.invoke(cz.run, request.text)
    return resp


@chat_router.post('/ask_model')
def ask_llm(request: AskLlmRequest):
    node = OpenAINode()
    node.conf.MODEL = request.model_name
    resp = asyncio.run(node.chat([UserMessage(request.text).to_message_dict()]))
    return resp


@chat_router.get('/callback')
def callback():
    return "ok"
