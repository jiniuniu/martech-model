import os
from contextlib import asynccontextmanager
from typing import Optional

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from common.config import env_settings
from common.qiniu_conn import get_qiniu
from svd_service.auth import get_token
from svd_service.utils import validate_image_file
from worker.app import app as celery_app

q = get_qiniu()

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


@app.get("/celery_health_check")
async def celery_health_check():
    task = celery_app.send_task("health_check", args=[3, 4])
    return {"task_id": task.id}


@app.post("/img2vid/create_task")
async def create_img2vid_task(file: UploadFile = File(None), img_key: str = Form(None)):
    if file and img_key:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": "Please provide either a file or an image URL, not both."
            },
        )
    if not file and not img_key:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Please provide either a file or an image URL."},
        )

    try:
        if file:
            img_path = validate_image_file(upload_file=file)
        else:
            out_dir = os.path.join(env_settings.DATA_DIR, "svd_materials")
            if not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            img_path = q.download_file(
                img_key,
                output_dir=out_dir,
            )
        task = celery_app.send_task("img_to_video", args=[img_path])
        return {"task_id": task.id}
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "message": e.detail,
            },
        )


@app.get("/task_status/{task_id}")
async def check_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    status = task_result.status

    if task_result.state == "PENDING":
        return {"status": "in_queue"}
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
