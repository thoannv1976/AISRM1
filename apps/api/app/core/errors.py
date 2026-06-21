"""Business error types and RFC7807-like problem details handlers."""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base business error mapped to a problem-details response."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"
    title: str = "Application error"

    def __init__(self, detail: str | None = None, *, field_errors: dict | None = None):
        self.detail = detail or self.title
        self.field_errors = field_errors or {}
        super().__init__(self.detail)


class AuthForbidden(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "AUTH_FORBIDDEN"
    title = "Không có quyền trong phạm vi yêu cầu."


class AuthUnauthorized(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTH_UNAUTHORIZED"
    title = "Yêu cầu xác thực."


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    title = "Không tìm thấy bản ghi."


class EntityVersionConflict(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "ENTITY_VERSION_CONFLICT"
    title = "Bản ghi đã thay đổi; tải lại trước khi lưu."


class InvalidStateTransition(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "INVALID_STATE_TRANSITION"
    title = "Không thể thực hiện hành động ở trạng thái hiện tại."


class SubmissionIncomplete(AppError):
    status_code = 422
    code = "SUBMISSION_INCOMPLETE"
    title = "Thiếu trường/tài liệu/checklist."


class DeadlinePassed(AppError):
    status_code = 422
    code = "DEADLINE_PASSED"
    title = "Đã quá hạn và không có override hợp lệ."


class DocumentQuarantined(AppError):
    status_code = status.HTTP_423_LOCKED
    code = "DOCUMENT_QUARANTINED"
    title = "Tệp chưa vượt kiểm tra an toàn."


class ConflictOfInterest(AppError):
    status_code = 422
    code = "CONFLICT_OF_INTEREST"
    title = "Reviewer có xung đột bị chặn."


class AICitationRequired(AppError):
    status_code = 422
    code = "AI_CITATION_REQUIRED"
    title = "Tính năng fact-based thiếu nguồn."


class AIFeatureDisabled(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "AI_FEATURE_DISABLED"
    title = "Tính năng AI tắt hoặc quota hết."


class RateLimited(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMITED"
    title = "Vượt hạn mức; thử lại sau."


class ValidationFailed(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"
    title = "Dữ liệu không hợp lệ."


def _problem(
    request: Request,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    field_errors: dict[str, Any] | None = None,
) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    body = {
        "type": f"about:blank#{code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "code": code,
        "field_errors": field_errors or {},
        "trace_id": trace_id,
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _problem(request, exc.status_code, exc.code, exc.title, exc.detail, exc.field_errors)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        field_errors: dict[str, str] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            field_errors[loc or "_"] = err.get("msg", "invalid")
        return _problem(
            request,
            422,
            "VALIDATION_FAILED",
            "Dữ liệu không hợp lệ.",
            "Một số trường không hợp lệ.",
            field_errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = {401: "AUTH_UNAUTHORIZED", 403: "AUTH_FORBIDDEN", 404: "NOT_FOUND"}.get(
            exc.status_code, "HTTP_ERROR"
        )
        return _problem(request, exc.status_code, code, "Lỗi yêu cầu", str(exc.detail))
