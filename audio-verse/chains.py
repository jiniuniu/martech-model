import base64
from typing import List

from config import env_settings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain.schema.messages import SystemMessage
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import create_async_engine

async_engine = create_async_engine(env_settings.MEMORY_URI)


def encode_image(img_path: str):
    with open(img_path, "rb") as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    return img_base64


def get_sql_chat_message_history(session_id: str) -> BaseChatMessageHistory:
    return SQLChatMessageHistory(session_id, connection=async_engine)


def build_vision_chat_chain(
    llm: ChatOpenAI,
    sys_msg: str,
    image_paths: List[str] = None,
) -> RunnableWithMessageHistory:
    messages = [
        SystemMessage(content=sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
    ]
    if image_paths:
        human_message = (
            "human",
            [
                {"type": "text", "text": "{user_input}"},
            ],
        )
        for image_path in image_paths:
            image_base64 = encode_image(image_path)
            img_data = {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{image_base64}",
            }
            human_message[1].append(img_data)
    else:
        human_message = ("human", "{user_input}")
    messages.append(human_message)
    prompt_template = ChatPromptTemplate.from_messages(messages)
    chain = prompt_template | llm | StrOutputParser()
    return RunnableWithMessageHistory(
        chain,
        get_sql_chat_message_history,
        input_messages_key="user_input",
        history_messages_key="chat_history",
    )



