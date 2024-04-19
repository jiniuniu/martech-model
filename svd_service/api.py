import os
from io import BytesIO
from typing import Annotated

import shortuuid
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, UploadFile
from loguru import logger
from PIL import Image
from starlette.middleware.cors import CORSMiddleware

from common.config import env_settings
from common.service_auth import get_token
from common.sqlite3_conn import get_db_connection
from svd_service.schemas import (
    BaseResponse,
    CheckTaskResponse,
    CreateTaskResponse,
    TaskStatus,
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


def updata_task_status_in_db(
    task_id: str,
    task_status: str,
    video_url: str,
):
    conn = get_db_connection()
    conn.execute(
        "UPDATE tasks SET status = ?, video_url = ? WHERE task_id = ?",
        (task_status, video_url, task_id),
    )
    conn.commit()
    conn.close()


def get_task_data_from_db(task_id):
    conn = get_db_connection()
    task = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(task)


def generate_video_task(task_id: str, motion_bucket_id: str):
    material_dir = os.path.join(env_settings.DATA_DIR, "svd_materials")
    img_path = os.path.join(material_dir, f"imgid-{task_id}.png")
    video_path = os.path.join(material_dir, f"vid-{task_id}.mp4")
    video_url = generate_video_from_img(
        image_path=img_path,
        output_path=video_path,
        motion_bucket_id=motion_bucket_id,
        noise_aug_strength=0.02,
    )
    if len(video_url) == 0:
        task_status = TaskStatus.FAILURE
    else:
        task_status = TaskStatus.SUCCESS

    updata_task_status_in_db(
        task_id,
        task_status,
        video_url,
    )
    return


@app.post("/create_video_gen_task")
async def create_video_gen_task(
    image: Annotated[UploadFile, File()],
    motion_bucket_id: Annotated[str, Form()],
    background_tasks: BackgroundTasks,
) -> BaseResponse:
    try:
        img = Image.open(BytesIO(await image.read()))
        task_id = shortuuid.ShortUUID().random(length=11)
        material_dir = os.path.join(env_settings.DATA_DIR, "svd_materials")
        if not os.path.exists(material_dir):
            os.mkdir(material_dir)
        img_path = os.path.join(material_dir, f"imgid-{task_id}.png")
        img.save(img_path)
        background_tasks.add_task(
            generate_video_task,
            task_id,
            motion_bucket_id,
        )
        status = TaskStatus.IN_PROGRESS
        video_url = ""
        updata_task_status_in_db(
            task_id,
            status,
            video_url,
        )
        return CreateTaskResponse(task_id=task_id)
    except Exception as e:
        logger.error(f"Error: {e}")
        return BaseResponse(code=500, msg="server error")


@app.get("/tasks/{task_id}/status")
async def check_status(task_id: str) -> BaseResponse:
    task_data = get_task_data_from_db(task_id)
    if not task_data:
        return BaseResponse(code=400, msg="task not found")
    status = task_data.get("status")
    video_url = task_data.get("video_url")
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
