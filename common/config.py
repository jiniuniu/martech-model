try:
    from pydantic import BaseSettings
except:
    from pydantic.v1 import BaseSettings


class EnvironmentSetting(BaseSettings):

    # redis for celery backend and task queue tracking
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_PWD: str

    # local data storage
    DATA_DIR: str

    # qiniu cloud service video file storage
    QINIU_AK: str
    QINIU_SK: str
    QINIU_BUCKET_NAME: str
    QINIU_BUCKET_DOMAIN: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


env_settings = EnvironmentSetting()
