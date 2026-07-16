import logging
import tomllib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.notifications import router as notifications_router
from api.v2.v2 import router as v2_router
from settings import settings

logger = logging.getLogger(__name__)


def get_service_version() -> str:
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"

    try:
        with pyproject_path.open("rb") as file:
            project_data = tomllib.load(file)

        return str(project_data["tool"]["poetry"]["version"])
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError):
        return "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    timeout = httpx.Timeout(settings.REQUEST_TIMEOUT)

    app.state.http_client = httpx.AsyncClient(
        timeout=timeout,
        proxy=settings.PROXY_URL,
    )

    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="Gate Namba One",
    description="Payment gateway integration with Namba One",
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    version=get_service_version(),
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.warning(
        "Request validation failed: method=%s path=%s errors=%s",
        request.method,
        request.url.path,
        exc.errors(),
    )

    return JSONResponse(
        status_code=422,
        content={
            "status": "failed",
            "code": "validation_error",
            "message": "Request data is not valid",
            "details": exc.errors(),
        },
    )


@app.get(
    "/v2/ping",
    tags=["service"],
)
async def ping() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "gate-nambaone",
        "version": get_service_version(),
    }


app.include_router(
    v2_router,
    prefix="/v2",
)

app.include_router(
    notifications_router,
    prefix="/notifications",
)


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    uvicorn.run(
        "main:app",
        host=settings.WEB_SERVICE_HOST,
        port=settings.WEB_SERVICE_PORT,
        log_level=settings.LOG_LEVEL,
        reload=settings.DEBUG,
    )