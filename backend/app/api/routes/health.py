from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.job import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    from app.infrastructure.whisper import get_model

    try:
        model = get_model()
        model_name = getattr(model, "model_size_or_path", settings.WHISPER_MODEL)
    except Exception:
        model_name = "not loaded"

    return HealthResponse(
        status="ok",
        version="2.0.0",
        whisper_model=str(model_name),
        mode="local (offline)",
    )
