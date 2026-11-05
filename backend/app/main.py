from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.categories import router as categories_router
from app.api.routes.evidences import router as evidences_router
from app.api.routes.findings import router as findings_router
from app.api.routes.health import router as health_router
from app.api.routes.labs import router as labs_router
from app.api.routes.platforms import router as platforms_router
from app.api.routes.reports import router as reports_router
from app.core.config import settings
from app.services.errors import ServiceError


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
    application.add_exception_handler(ServiceError, service_error_handler)
    application.include_router(health_router)
    application.include_router(platforms_router)
    application.include_router(categories_router)
    application.include_router(labs_router)
    application.include_router(evidences_router)
    application.include_router(findings_router)
    application.include_router(reports_router)
    return application


async def service_error_handler(_: Request, service_error: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=service_error.status_code,
        content={"detail": service_error.detail},
    )


app = create_app()
