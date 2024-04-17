import os
from io import BytesIO

import shortuuid
from fastapi import BackgroundTasks, Depends, FastAPI, UploadFile
from loguru import logger
from PIL import Image
from starlette.middleware.cors import CORSMiddleware

from common.config import env_settings
from common.redis_conn import get_redis
from common.service_auth import get_token
from svd_service.schemas import (
    BaseResponse,
    CheckTaskResponse,
    CreateTaskResponse,
    TaskStatus,
    VideoGenParam,
)
from svd_service.svd import generate_video_from_img

deps = [Depends(get_token)]


app = FastAPI(dependencies=deps)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=(
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ),
    allow_headers=["*"],
)


def generate_video_task(task_id: str, video_gen_param: VideoGenParam):
    task_key = f"task-id-{task_id}"
    conn = get_redis()
    img_path = os.path.join(env_settings.IMG_DIR, f"imgid-{task_id}.png")
    video_path = os.path.join(env_settings.IMG_DIR, f"vid-{task_id}.mp4")
    motion_bucket_id = video_gen_param.motion_bucket_id
    noise_aug_strength = video_gen_param.noise_aug_strength
    video_url = generate_video_from_img(
        image_path=img_path,
        output_path=video_path,
        motion_bucket_id=motion_bucket_id,
        noise_aug_strength=noise_aug_strength,
    )
    if len(video_url) == 0:
        task_data = {
            "status": TaskStatus.FAILURE,
        }
    else:
        task_data = {
            "status": TaskStatus.SUCCESS,
            "video_url": video_url,
        }

    conn.hset(task_key, mapping=task_data)
    return


def check_image_size(
    image: Image.Image,
    desired_size: tuple[int, int] = (1024, 576),
) -> bool:
    return image.size == desired_size


@app.post("/create_video_gen_task")
async def create_video_gen_task(
    video_gen_param: VideoGenParam,
    image: UploadFile,
    background_tasks: BackgroundTasks,
) -> BaseResponse:
    try:
        img = Image.open(BytesIO(await image.read()))
        ok = check_image_size(img)
        if not ok:
            return BaseResponse(
                code=400,
                msg="only allowable size: 1024x576",
            )
        task_id = shortuuid.ShortUUID().random(length=11)
        img_path = os.path.join(env_settings.IMG_DIR, f"imgid-{task_id}.png")
        img.save(img_path)
        background_tasks.add_task(generate_video_task, task_id, video_gen_param)
        conn = get_redis()
        task_key = f"task-id-{task_id}"
        task_data = {"status": TaskStatus.IN_PROGRESS}
        conn.hset(task_key, mapping=task_data)
        return CreateTaskResponse(task_id=task_id)
    except Exception as e:
        logger.error(f"Error: {e}")
        return BaseResponse(code=500, msg="server error")


@app.get("/tasks/{task_id}/status")
async def check_status(task_id: str) -> BaseResponse:
    conn = get_redis()
    task_key = f"task-id-{task_id}"
    task_data = conn.hgetall(task_key)
    if len(task_data) == 0:
        return BaseResponse(code=400, msg="task not found")
    status = task_data.get("status")
    video_url = task_data.get("video_url") or ""
    return CheckTaskResponse(
        status=status,
        video_url=video_url,
    )


@app.get("/health")
async def health():
    return {"message": "ok"}


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=27777)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
