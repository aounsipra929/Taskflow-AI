"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.routes import admin, auth, chat, tasks, users
from app.core.config import settings
from app.db.init_db import create_first_admin

logger = logging.getLogger("todo")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        create_first_admin()
    except SQLAlchemyError:
        logger.exception("Could not bootstrap admin (did you run `alembic upgrade head`?)")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Full-stack To-Do application API with JWT auth and admin/user roles.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix=settings.API_V1_PREFIX)
for module in (auth, users, tasks, admin, chat):
    api_router.include_router(module.router)
app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


# ---- Global error handlers -------------------------------------------------
@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    logger.warning("Integrity error: %s", exc)
    return JSONResponse(status_code=409, content={"detail": "Database constraint violated"})


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(_: Request, exc: SQLAlchemyError):
    logger.exception("Database error")
    return JSONResponse(status_code=500, content={"detail": "A database error occurred"})
