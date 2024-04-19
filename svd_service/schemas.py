from enum import Enum

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    code: int = Field(200, description="API status code")
    msg: str = Field("success", description="API status message")


class CreateTaskResponse(BaseResponse):
    task_id: str = Field(..., description="任务的ID")


class TaskStatus(str, Enum):

    IN_PROGRESS: str = "in-progress"
    SUCCESS: str = "success"
    FAILURE: str = "failure"


class CheckTaskResponse(BaseResponse):
    status: TaskStatus = Field(..., description="任务的状态，三种可能性")
    video_url: str = Field("", description="视频的链接")
