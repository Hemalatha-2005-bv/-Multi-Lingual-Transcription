"""
Google Cloud Storage helper service.
Provides upload and delete operations for temporary audio files.
"""

import asyncio
import logging
from functools import lru_cache

from google.cloud import storage

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _get_client() -> storage.Client:
    return storage.Client(project=settings.GCP_PROJECT_ID)


async def upload_to_gcs(local_path: str, blob_name: str) -> str:
    """
    Upload a local file to GCS and return its gs:// URI.
    Runs the blocking GCS call in the default thread pool executor.
    """
    loop = asyncio.get_event_loop()

    def _upload():
        client = _get_client()
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        gcs_uri = f"gs://{settings.GCS_BUCKET_NAME}/{blob_name}"
        logger.info("Uploaded %s → %s", local_path, gcs_uri)
        return gcs_uri

    return await loop.run_in_executor(None, _upload)


async def delete_from_gcs(blob_name: str) -> None:
    """
    Delete a blob from GCS. Logs a warning if the blob doesn't exist
    rather than raising an exception — cleanup should never crash a job.
    """
    loop = asyncio.get_event_loop()

    def _delete():
        client = _get_client()
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
            logger.info("Deleted GCS blob: %s", blob_name)
        else:
            logger.warning("GCS blob not found (skipping delete): %s", blob_name)

    await loop.run_in_executor(None, _delete)
