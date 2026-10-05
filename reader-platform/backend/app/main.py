from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  registers all tables on Base.metadata
from .config import settings
from .db import Base, engine
from .routers import series


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience. Step 2 replaces this with Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Reader Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(series.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
