"""
@Author: obstacle
@Time: 21/01/25 11:54
@Description:  
"""
from pydantic import BaseModel
from typing import Dict, List


class ImageModel(BaseModel):
    model: str = "sd-turbo"
    size: str = "256*256"


class PreprocessModel(BaseModel):
    model: str = ""
    temperature: float = 0.05
    max_tokens: int = 4096
    history_len: int = 10
    prompt_name: str = "default"
    callbacks: bool = False


class LLMModel(BaseModel):
    model: str = ""
    temperature: float = 0.8
    max_tokens: int = 4096
    history_len: int = 10
    prompt_name: str = "x"
    callbacks: bool = True


class ActionModel(BaseModel):
    model: str = ""
    temperature: float = 0.01
    max_tokens: int = 4096
    history_len: int = 10
    prompt_name: str = "ChatGLM3"
    callbacks: bool = True


class PostprocessModel(BaseModel):
    model: str = ""
    temperature: float = 0.01
    max_tokens: int = 4096
    history_len: int = 10
    prompt_name: str = "default"
    callbacks: bool = True


class ChatModelConfig(BaseModel):
    preprocess_model: PreprocessModel
    llm_model: LLMModel
    action_model: ActionModel
    postprocess_model: PostprocessModel
    image_model: ImageModel


class ChatRequest(BaseModel):
    query: str
    chat_type: int
    bot_name: str = "Toto"
    metadata: Dict = {}
    conversation_id: str = ""
    message_id: str = "string"
    history_len: int = -1
    history: List = []
    chat_model_config: ChatModelConfig
    stream: bool = False
    tool_config: Dict = {}
    max_tokens: int = 0
