from common.config import EnvironmentSetting


class WorkerEnvironmentSetting(EnvironmentSetting):

    SVD_MODEL_DIR: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


env_settings = WorkerEnvironmentSetting()
