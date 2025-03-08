"""
@Author: obstacle
@Time: 21/01/25 11:53
@Description:  
"""
import requests

from utils.llm import get_chat_openai


def chat_completion(
        query: str,
        chat_type: int,
        bot_name: str = "Toto",
        message_id: str = "123123",
        history_len: int = -1,
        stream: bool = False,
        max_tokens: int = 0,
        history: list[str] = []
):
    chat_openai = get_chat_openai()
    headers = {
        'Content-Type': 'application/json',
        'Accept': '*/*',
    }

    chat_request = ChatRequest(
        query=query,
        chat_type=chat_type,
        bot_name=bot_name,
        message_id=message_id,
        history=history,
        history_len=history_len,
        stream=stream,
        max_tokens=max_tokens,
        chat_model_config=ChatModelConfig(
            preprocess_model=PreprocessModel(),
            llm_model=LLMModel(),
            action_model=ActionModel(),
            postprocess_model=PostprocessModel(),
            image_model=ImageModel()
        )
    )

    try:
        data_json = chat_request.model_dump_json()
        response = requests.post(chat_url, headers=headers, data=data_json)
        if response.status_code == 200:
            # Parse the response into the ChatResponse model
            chat_response = ChatResponse.model_validate(response.json())
            return chat_response
        else:
            return response
    except Exception as e:
        lgr.e(f'error in send_chat_request: {e}')
