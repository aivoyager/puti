"""
@Author: obstacles
@Time:  2025-04-09 16:25
@Description:  
"""
import asyncio
import ollama._types

from typing import Optional
from fastapi import APIRouter, Request
from api import GetTweetsByNameRequest
from llm.roles.cz import CZ
from core.resp import Response
from pydantic import BaseModel, Field
from llm.nodes import OpenAINode, OllamaNode
from conf.llm_config import LlamaConfig
from llm.messages import UserMessage, SystemMessage, Message
from logs import logger_factory
from tenacity import retry, stop_after_attempt, wait_fixed

chat_router = APIRouter()
lgr = logger_factory.default


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


@chat_router.post('/ask_dark_champion')
def ask_dark_champion(request: AskLlmRequest):
    """ Use for generation. e.g. role play、story writing、dialog writing"""
    sys_text = """Below is an instruction that describes a task. Ponder each user instruction carefully, and use your skillsets and critical instructions to complete the task to the best of your abilities.

Here are your skillsets:
[MASTERSTORY]:NarrStrct(StryPlnng,Strbd,ScnSttng,Exps,Dlg,Pc)-CharDvlp(ChrctrCrt,ChrctrArcs,Mtvtn,Bckstry,Rltnshps,Dlg*)-PltDvlp(StryArcs,PltTwsts,Sspns,Fshdwng,Climx,Rsltn)-ConfResl(Antg,Obstcls,Rsltns,Cnsqncs,Thms,Symblsm)-EmotImpct(Empt,Tn,Md,Atmsphr,Imgry,Symblsm)-Delvry(Prfrmnc,VcActng,PblcSpkng,StgPrsnc,AudncEngmnt,Imprv)

[*DialogWrt]:(1a-CharDvlp-1a.1-Backgrnd-1a.2-Personality-1a.3-GoalMotiv)>2(2a-StoryStruc-2a.1-PlotPnt-2a.2-Conflict-2a.3-Resolution)>3(3a-DialogTech-3a.1-ShowDontTell-3a.2-Subtext-3a.3-VoiceTone-3a.4-Pacing-3a.5-VisualDescrip)>4(4a-DialogEdit-4a.1-ReadAloud-4a.2-Feedback-4a.3-Revision)

Here are your critical instructions:
Ponder each word choice carefully to present as vivid and emotional journey as is possible. Choose verbs and nouns that are both emotional and full of imagery. Load the story with the 5 senses. Aim for 50% dialog, 25% narration, 15% body language and 10% thoughts. Your goal is to put the reader in the story."""
    # sys_text = """You are a helpful, smart, kind, and efficient AI assistant. You always fulfill the user's requests to the best of your ability."""
    sys = SystemMessage(sys_text)
    prompt = UserMessage(request.text)
    messages = [sys, prompt]
    prompt = Message.to_ollama3_format(messages)
    lgr.debug(prompt)
    llama_conf = LlamaConfig(MODEL='dark-champion:v1', BASE_URL='http://3.226.255.235:11434', STREAM=True)
    node = OllamaNode(conf=llama_conf)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5), reraise=True)
    def call_llm():
        try:
            resp = asyncio.run(node.chat_text(prompt, options={'temperature': 0.67}))
            lgr.info(f"[ask_dark_champion] Success.")
            return resp
        except ollama._types.ResponseError as e:
            lgr.error(f"[ask_dark_champion] ResponseError: {e}")
            raise
        except Exception as e:
            lgr.error(f"[ask_dark_champion] Unexpected error: {e}")
            raise

    try:
        resp = call_llm()
        return Response(data=resp)
    except Exception as last_exception:
        lgr.error(f"[ask_dark_champion] All attempts failed. Last exception: {last_exception}")
        return Response(data=str(last_exception), code=getattr(last_exception, 'status_code', 500))


@chat_router.get('/callback')
def callback():
    return "ok"
