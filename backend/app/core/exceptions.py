import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from loguru import logger
from starlette.responses import JSONResponse

from app.common.errors import BizError, ErrorCode


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id", uuid.uuid4().hex)
        return JSONResponse(
            status_code=200,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": None,
                "requestId": request_id,
                "timestamp": datetime.now(UTC).astimezone().isoformat(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id", uuid.uuid4().hex)
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "code": ErrorCode.PARAM_ERROR,
                "message": "参数校验失败",
                "data": exc.errors(),
                "requestId": request_id,
                "timestamp": datetime.now(UTC).astimezone().isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id", uuid.uuid4().hex)
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "服务内部错误",
                "data": None,
                "requestId": request_id,
                "timestamp": datetime.now(UTC).astimezone().isoformat(),
            },
        )
