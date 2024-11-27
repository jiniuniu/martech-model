from pydantic_settings import BaseSettings


class EnvironmentSettings(BaseSettings):

    base_url: str
    api_key: str
    llm_name: str
    memory_uri: str
    whisper_model_path: str
    f5_model_path: str
    qiniu_ak: str
    qiniu_sk: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


env_settings = EnvironmentSettings()
