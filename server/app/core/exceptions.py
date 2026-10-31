from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class VaaniException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        retryable: bool = False,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details
        super().__init__(message)


class NotVerifiedException(VaaniException):
    def __init__(self, message: str = "Customer verification is required before proceeding."):
        super().__init__(
            code="NOT_VERIFIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            retryable=False,
        )


class AuthMismatchException(VaaniException):
    def __init__(self, message: str = "Customer verification details do not match.", retryable: bool = True):
        super().__init__(
            code="AUTH_MISMATCH",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            retryable=retryable,
        )


class LockedSessionException(VaaniException):
    def __init__(self, message: str = "Session locked due to 3 failed verification attempts. Please contact a human agent."):
        super().__init__(
            code="LOCKED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            retryable=False,
        )


class ResourceNotFoundException(VaaniException):
    def __init__(self, message: str = "The requested banking resource was not found."):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=False,
        )


class ConflictException(VaaniException):
    def __init__(self, message: str = "Conflict with existing resource."):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            retryable=False,
        )


async def vaani_exception_handler(request: Request, exc: VaaniException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
            }
        },
    )

