from config import env_settings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.messages import SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=env_settings.LLM_API_KEY,
        base_url=env_settings.LLM_API_ENDPOINT,
        model=env_settings.LLM_NAME,
    )


def build_chat_chain(sys_msg: str) -> RunnableWithMessageHistory:
    llm = get_llm()
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=sys_msg),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{prompt}"),
        ]
    )
    chain = prompt_template | llm | StrOutputParser()

    chat_message_history = ChatMessageHistory()
    return RunnableWithMessageHistory(
        chain,
        lambda _: chat_message_history,
        input_messages_key="prompt",
        history_messages_key="chat_history",
    )


def build_vision_chain(sys_msg: str):
    llm = get_llm()
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=sys_msg),
            (
                "human",
                [
                    {"type": "text", "text": "{prompt}"},
                    {
                        "type": "image_url",
                        "image_url": "data:image/jpeg;base64,{image_base64}",
                    },
                ],
            ),
        ]
    )
    chain = prompt_template | llm | StrOutputParser()
    return chain


if __name__ == "__main__":
    from prompts import CHAT_SYS_MSG

    chat_chain = build_chat_chain(CHAT_SYS_MSG)
    user_input = "tell me a story about Einstein."
    inp = {"prompt": user_input}
    for chunk in chat_chain.stream(
        inp,
        config={
            "configurable": {
                "session_id": "abc",
            },
        },
    ):
        print(chunk, end="", flush=True)
