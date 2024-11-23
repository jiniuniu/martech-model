from pydantic_settings import BaseSettings


class EnvironmentSetting(BaseSettings):

    LLM_API_KEY: str
    LLM_API_ENDPOINT: str
    LLM_NAME: str
    WHISPER_MODEL_PATH: str
    F5_TTS_CKPT_PATH: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


env_settings = EnvironmentSetting()
