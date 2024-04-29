import os

import shortuuid
from celery import Celery
from loguru import logger

from common.config import env_settings
from common.qiniu_conn import get_qiniu
from worker.tasks.health_check import simulate_long_task
from worker.tasks.svd import generate_video_from_img

qiniu = get_qiniu()

HOST = env_settings.REDIS_HOST
PORT = env_settings.REDIS_PORT
PWD = env_settings.REDIS_PWD


app = Celery(
    "video-gen-tasks",
    broker=f"redis://:{PWD}@{HOST}:{PORT}/0",
    backend=f"redis://:{PWD}@{HOST}:{PORT}/0",
    include=["worker.tasks"],
)
app.conf.task_serializer = "json"
app.conf.result_expires = 86400  # 1 day in seconds


@app.task(name="health_check")
def test_celery(a: int, b: int):
    x = simulate_long_task()
    res = x + a + b
    return {"result": res}


@app.task(name="img_to_video")
def img_to_video(image_path: str) -> dict:
    try:
        file_dir = os.path.dirname(image_path)
        vid = shortuuid.ShortUUID().random(length=11)
        output_path = os.path.join(file_dir, f"vid-{vid}.mp4")
        ok = generate_video_from_img(
            image_path=image_path,
            output_path=output_path,
        )

        if ok:
            video_key = qiniu.upload_file(
                output_path,
                upload_dir="svd_materials",
            )
            os.remove(image_path)
            os.remove(output_path)
            return {"url": f"{env_settings.QINIU_BUCKET_DOMAIN}/{video_key}"}
    except Exception as exc:
        logger.error(f"Error generating video: {exc}")
    return {}
