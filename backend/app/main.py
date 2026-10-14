import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.scanner_ws import router as scanner_ws_router
from app.api.v1.router import api_router
from app.core.errors import AppError, app_error_handler
from app.core.logging import request_id_ctx, setup_logging
from app.core.settings import get_settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(debug=settings.debug)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(scanner_ws_router)
    return app


app = create_app()
