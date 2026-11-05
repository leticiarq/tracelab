from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.routes.categories import router as categories_router
from app.api.routes.evidences import router as evidences_router
from app.api.routes.health import router as health_router
from app.api.routes.labs import router as labs_router
from app.api.routes.platforms import router as platforms_router
from app.api.routes.reports import router as reports_router
from app.core.config import settings
from app.services.errors import ServiceError


class LocalRequestSecurityMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed_origins = {item.rstrip("/") for item in allowed_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in scope["headers"]
            }
            origin = headers.get("origin")
            fetch_site = headers.get("sec-fetch-site", "").lower()
            if fetch_site == "cross-site" or (
                origin is not None and origin.rstrip("/") not in self.allowed_origins
            ):
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Cross-site request rejected"},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.cors_origins],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )
    application.add_middleware(
        LocalRequestSecurityMiddleware,
        allowed_origins=settings.cors_origins,
    )

    application.add_exception_handler(ServiceError, service_error_handler)
    application.include_router(health_router)
    application.include_router(platforms_router)
    application.include_router(categories_router)
    application.include_router(labs_router)
    application.include_router(evidences_router)
    application.include_router(reports_router)
    return application


async def service_error_handler(_: Request, service_error: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=service_error.status_code,
        content={"detail": service_error.detail},
    )
app = create_app()
