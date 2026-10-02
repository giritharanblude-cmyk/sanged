from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    code: str


class AppError(Exception):
    def __init__(self, status: int, code: str, detail: str) -> None:
        self.status = status
        self.code = code
        self.detail = detail


def problem_response(
    status: int,
    code: str,
    detail: str,
    instance: str | None = None,
) -> JSONResponse:
    body = ProblemDetail(
        status=status,
        code=code,
        title=code.replace("_", " ").title(),
        detail=detail,
        instance=instance,
    )
    return JSONResponse(status_code=status, content=body.model_dump())


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return problem_response(exc.status, exc.code, exc.detail, str(request.url))
