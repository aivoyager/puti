"""
@Author: obstacles
@Time:  2025-06-13 16:47
@Description:  
"""
from puti.constant.llm import RoleType
from puti.llm.messages import Message


def test_convert_image_request_to_messages():
    data = [
        {"type": "text", "text": 'hi'},
        {
            "type": "image_url",
            "image_url": {
                "url": 'test.url in base64'
            }
        }
    ]
    message = Message.from_any(msg=data, role=RoleType.USER)
    message_dic = message.to_message_dict()
    print(message_dic)


def test_image():
    msg = Message.image('hi', 'test_url')
    print(msg.to_message_dict())

    print(Message.to_message_list([msg]))
