import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from loguru import logger
from pydantic import ValidationError
from starlette.responses import JSONResponse

from app.common.errors import BizError, ErrorCode


def _safe_errors(exc: ValidationError | RequestValidationError) -> list[dict[str, Any]]:
    """Return JSON-serializable validation errors.

    pydantic's ``exc.errors()`` may embed the original exception object in
    ``ctx.error`` (e.g. a ``ValueError``), which is not JSON serializable
    and turns a 422 into a 500. We strip ``ctx`` down to its message.
    """
    errors = exc.errors()
    safe: list[dict[str, Any]] = []
    for err in errors:
        item = dict(err)
        ctx = item.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            item["ctx"] = {k: (str(v) if k == "error" else v) for k, v in ctx.items()}
        safe.append(item)
    return safe


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
                "data": _safe_errors(exc),
                "requestId": request_id,
                "timestamp": datetime.now(UTC).astimezone().isoformat(),
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id", uuid.uuid4().hex)
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "code": ErrorCode.PARAM_ERROR,
                "message": "参数校验失败",
                "data": _safe_errors(exc),
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
