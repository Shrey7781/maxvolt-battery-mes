import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionLocal
from app.envelope import RTN, MESError, StandardResponse
from app.rate_limit import limiter
from app.routers import cell, module, pack

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("mes")

app = FastAPI(
    title="MaxVolt Energy - Battery Production Line MES API",
    version="1.0.0",
    description="Backend for the robotic battery assembly line station interfaces.",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.include_router(cell.router)
app.include_router(module.router)
app.include_router(pack.router)


def _envelope(rtn_code: int, msg: str) -> JSONResponse:
    # HTTP status is always 200 by design — see app/envelope.py.
    return JSONResponse(status_code=200, content=StandardResponse(rtnCode=rtn_code, msg=msg, data=None).model_dump())


@app.exception_handler(MESError)
async def mes_error_handler(request: Request, exc: MESError) -> JSONResponse:
    return _envelope(exc.rtn_code, exc.msg)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first["loc"] if part != "body")
    msg = f"{loc}: {first['msg']}" if loc else first["msg"]
    return _envelope(RTN.VALIDATION_ERROR, msg)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    # Backstop only — app.services.genealogy checks references before we
    # ever reach the database, so this should only fire on a race between
    # concurrent requests or a future code path that forgets that check.
    logger.warning("Integrity error on %s: %s", request.url.path, exc)
    if isinstance(exc.orig, pg_errors.ForeignKeyViolation):
        return _envelope(RTN.REFERENCE_NOT_FOUND, "Referenced entity does not exist")
    return _envelope(RTN.DUPLICATE, "Duplicate or conflicting record")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return _envelope(RTN.RATE_LIMITED, "Rate limit exceeded, slow down")


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return _envelope(RTN.INTERNAL_ERROR, "Internal server error")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}
