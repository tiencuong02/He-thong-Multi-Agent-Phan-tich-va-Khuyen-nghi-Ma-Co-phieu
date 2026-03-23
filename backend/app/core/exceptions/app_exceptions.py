from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class BaseAppException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

class ResourceNotFoundException(BaseAppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)

class ExternalServiceException(BaseAppException):
    def __init__(self, message: str = "External service error"):
        super().__init__(message, status_code=502)

async def app_exception_handler(request: Request, exc: BaseAppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "status": "error"}
    )

async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    # Don't expose internal error details in production-grade apps
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred", "status": "error"}
    )
