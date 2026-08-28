from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from sqlalchemy import text
from starlette.responses import Response

from .api import router
from .config import get_settings
from .db import SessionLocal, engine, init_db
from .seed import seed_demo_data

settings = get_settings()
REQUESTS = Counter(
    "deployledger_http_requests_total",
    "Total HTTP requests handled by DeployLedger.",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "deployledger_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    if settings.demo_seed:
        async with SessionLocal() as session:
            await seed_demo_data(session)
    yield
    await engine.dispose()


app_kwargs = {
    "title": "DeployLedger API",
    "version": "0.1.0",
    "lifespan": lifespan,
    "docs_url": "/docs" if settings.docs_enabled else None,
    "redoc_url": "/redoc" if settings.docs_enabled else None,
}
app = FastAPI(**app_kwargs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key", "X-Hub-Signature-256"],
)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    path = request.url.path
    REQUESTS.labels(request.method, path, response.status_code).inc()
    LATENCY.labels(request.method, path).observe(perf_counter() - started)
    return response


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "name": "deployledger-api",
        "version": "0.1.0",
        "docs": "/docs" if settings.docs_enabled else "disabled",
    }


@app.get("/health/live", tags=["system"])
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["system"])
async def ready() -> dict[str, str]:
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


app.include_router(router)
