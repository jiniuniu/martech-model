from pydantic_settings import BaseSettings


class EnvironmentSettings(BaseSettings):

    f5_model_path: str
    whisper_model_path: str
    sd35_model_path: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


env_settings = EnvironmentSettings()
