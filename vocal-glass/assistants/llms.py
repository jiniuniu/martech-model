from config import env_settings
from langchain_openai import ChatOpenAI


def get_llm(temperature=0.5) -> ChatOpenAI:

    llm = ChatOpenAI(
        model=env_settings.llm_name,
        base_url=env_settings.base_url,
        api_key=env_settings.api_key,
        streaming=True,
        temperature=temperature,
    )

    return llm
