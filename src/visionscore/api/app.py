from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from visionscore import __version__
from visionscore.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from visionscore.config import Settings

    app.state.settings = Settings()
    yield


app = FastAPI(
    title="VisionScore API",
    version=__version__,
    description="AI-powered photo evaluation API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
