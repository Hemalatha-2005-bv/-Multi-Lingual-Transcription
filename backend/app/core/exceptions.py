class AppError(Exception):
    """Base application error."""


class JobNotFoundError(AppError):
    def __init__(self, job_id: str):
        super().__init__(f"Job '{job_id}' not found.")
        self.job_id = job_id


class FileTooLargeError(AppError):
    def __init__(self, max_mb: int):
        super().__init__(f"File exceeds the {max_mb} MB limit.")
        self.max_mb = max_mb


class InvalidURLError(AppError):
    def __init__(self, url: str):
        super().__init__(f"'{url}' is not a supported YouTube URL.")
        self.url = url


class FFmpegError(AppError):
    pass


class WhisperError(AppError):
    pass


class DownloadError(AppError):
    pass
