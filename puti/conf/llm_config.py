"""
@Author: obstacles
@Time:  2025-03-03 16:23
@Description:  
"""
from puti.conf.config import Config
from puti.constant.base import Modules
from pydantic import ConfigDict, Field
from puti.constant.llm import LLM
from typing import Optional, Union
from openai.types.chat_model import ChatModel


class LLMConfig(Config):
    """ Universal LLM conf """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    API_KEY: Optional[str] = None
    MODEL: Optional[Union[str, ChatModel]] = None
    BASE_URL: Optional[str] = None

    EMBEDDING_MODEL: Optional[str] = None
    EMBEDDING_DIM: Optional[int] = None

    # All fields need default value
    MAX_TOKEN: Optional[int] = None
    TEMPERATURE: Optional[float] = None
    TOP_K: Optional[float] = None
    TOP_P: Optional[float] = None
    REPETITION_PENALTY: Optional[float] = None
    STOP: Optional[str] = None
    PRESENCE_PENALTY: Optional[float] = None
    FREQUENCY_PENALTY: Optional[float] = None
    BEST_OF: Optional[int] = None
    N: Optional[int] = None
    STREAM: Optional[bool] = None
    SEED: Optional[int] = None
    LOGPROBS: Optional[bool] = None
    TOP_LOGPROBS: Optional[int] = None
    CONTEXT_LENGTH: Optional[int] = None  # max input tokne
    LLM_API_TIMEOUT: Optional[int] = None
    VERBOSE: Optional[bool] = N


class OpenaiConfig(LLMConfig):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    FAISS_SEARCH_TOP_K: Optional[int] = None
    EMBEDDING_MODEL: str = Field(default=None, description='Embedding model name')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        parent = self.__class__.__bases__[0]
        parent_fields = parent.__annotations__.keys()
        field = self.__annotations__.keys() | parent_fields
        conf = self._subconfig_init(module=Modules.LLM.val, llm=LLM.OPENAI.val)
        for i in field:
            if not getattr(self, i):
                setattr(self, i, conf.get(i, None))


class LlamaConfig(LLMConfig):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        parent = self.__class__.__bases__[0]
        parent_fields = parent.__annotations__.keys()
        field = self.__annotations__.keys() | parent_fields
        conf = self._subconfig_init(module=Modules.LLM.val, llm=LLM.LLAMA.val)
        for i in field:
            if not getattr(self, i):
                setattr(self, i, conf.get(i, None))
