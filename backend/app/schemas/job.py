from typing import Any, Optional

from pydantic import BaseModel, Field


class UploadVideoRequest(BaseModel):
    language: str = Field(default="auto", description="ta-IN | en-US | auto")


class TranscribeURLRequest(BaseModel):
    url: str
    language: str = Field(default="auto", description="ta-IN | en-US | auto")


class JobCreatedResponse(BaseModel):
    job_id: str


class JobProcessingResponse(BaseModel):
    status: str = "processing"
    step: str
    progress: Optional[float] = None
    title: str = ""


class JobErrorResponse(BaseModel):
    status: str = "error"
    error: str
    title: str = ""


class WordResult(BaseModel):
    word: str
    start_time: float
    end_time: float


class SegmentResult(BaseModel):
    transcript: str
    confidence: float
    language_code: str
    words: list[WordResult]


class JobCompletedResponse(BaseModel):
    status: str = "completed"
    results: list[dict[str, Any]]
    txt: str
    srt: str
    title: str = ""


class HealthResponse(BaseModel):
    status: str
    version: str
    whisper_model: str
    mode: str
