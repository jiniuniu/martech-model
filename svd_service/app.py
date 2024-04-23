from contextlib import asynccontextmanager
from typing import Annotated

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from celery.result import AsyncResult
from fastapi import Depends, FastAPI, File, UploadFile
from starlette.middleware.cors import CORSMiddleware

from common.redis_conn import get_redis_conn
from svd_service.auth import get_token
from svd_service.utils import validate_image_file
from worker.app import app as celery_app

TASK_QUEUE_NAME = "img2vid_queue"
redis_client = get_redis_conn()


deps = [Depends(get_token)]


def cleanup_queue():
    for task_id in redis_client.lrange(TASK_QUEUE_NAME, 0, -1):
        result = AsyncResult(task_id, app=celery_app)
        if result.state in ["SUCCESS", "FAILURE"]:
            redis_client.lrem(TASK_QUEUE_NAME, 0, task_id)


scheduler = AsyncIOScheduler()
scheduler.add_job(
    cleanup_queue,
    "interval",
    minutes=60,
)  # Adjust the timing as necessary


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        scheduler.start()
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(dependencies=deps, lifespan=lifespan)


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


@app.get("/celery_health_check")
async def celery_health_check():
    task = celery_app.send_task("health_check", args=[3, 4])
    return {"task_id": task.id}


@app.post("/img2vid/create_task")
async def create_img2vid_task(image: Annotated[UploadFile, File()]):

    img_path = validate_image_file(image)

    task = celery_app.send_task("img_to_video", args=[img_path])
    redis_client.lpush(TASK_QUEUE_NAME, task.id)
    return {"task_id": task.id}


@app.get("/img2vid/task_status/{task_id}")
async def check_img2vid_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    status = task_result.status

    if task_result.state == "PENDING":
        queue = redis_client.lrange(TASK_QUEUE_NAME, 0, -1)
        position = queue.index(task_id) + 1 if task_id in queue else None
        if position:
            return {"status": "in_queue", "position": position}
        else:
            return {"status": "not_found"}
    elif status == "STARTED":
        return {"status": "running"}
    elif status == "SUCCESS":
        result = task_result.result
        if result and "url" in result:
            return {"status": "success", "url": result["url"]}
        else:
            return {
                "status": "success",
                "message": "Task completed but no URL returned.",
            }
    elif status == "FAILURE":
        return {
            "status": "failure",
            "message": task_result.traceback or "Unknown error",
        }
    return {"status": "unknown", "message": status}


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
