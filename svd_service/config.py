from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()


class EnvironmentSetting(BaseSettings):

    SERVICE_ACCESS_TOKEN: str
    SVD_MODEL_DIR: str

    # my data directory
    DATA_DIR: str

    # redis
    REDIS_HOST: str
    REDIS_PORT: str

    # qiniu cloud service
    QINIU_AK: str
    QINIU_SK: str
    QINIU_BUCKET_NAME: str
    QINIU_BUCKET_DOMAIN: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


env_settings = EnvironmentSetting()
