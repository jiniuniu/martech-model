import os
import shutil
from functools import lru_cache

import requests
from loguru import logger
from qiniu import Auth, BucketManager, put_file

from common.config import env_settings


class QiNiuConnector:

    def __init__(self):
        self.q = Auth(env_settings.QINIU_AK, env_settings.QINIU_SK)
        self.bucket_manager = BucketManager(self.q)
        self.bucket_name = env_settings.QINIU_BUCKET_NAME
        self.bucket_domain = env_settings.QINIU_BUCKET_DOMAIN

    def get_public_url(self, file_key: str):
        return "https://%s/%s" % (self.bucket_domain, file_key)

    def _get_private_url(self, file_key: str):
        base_url = self.get_public_url(file_key)
        return self.q.private_download_url(base_url)

    def upload_file(self, local_file_path: str, upload_dir: str):
        file = os.path.basename(local_file_path)
        upload_key = f"{upload_dir}/{file}"
        token = self.q.upload_token(self.bucket_name, upload_key)
        res, info = put_file(token, upload_key, local_file_path, version="v2")
        return upload_key

    def download_file(self, file_key: str, output_dir: str) -> str:
        url = self._get_private_url(file_key)
        resp = requests.get(url, stream=True)
        filename = os.path.basename(file_key)
        output_path = os.path.join(output_dir, filename)
        try:
            resp.raise_for_status()
            with open(output_path, "wb") as file:
                # Use shutil.copyfileobj to copy the response stream to the file
                shutil.copyfileobj(resp.raw, file)
            return output_path
        except Exception as e:
            logger.error(f"error: {e}")
            return ""


@lru_cache(1)
def get_qiniu():
    qiniu = QiNiuConnector()
    return qiniu


if __name__ == "__main__":
    q = get_qiniu()
    img_key = "svd_materials/still_frames/1783379873989922816.png"
    output_path = q.download_file(img_key, ".")
    print(output_path)
