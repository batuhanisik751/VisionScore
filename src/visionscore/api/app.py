from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from visionscore import __version__
from visionscore.api.routes import router

logger = logging.getLogger(__name__)


async def _webhook_retry_loop(app: FastAPI) -> None:
    """Background task that retries failed webhook deliveries every 60s."""
    while True:
        await asyncio.sleep(60)
        try:
            from visionscore.api.supabase_client import get_supabase_client
            from visionscore.api.webhooks import WebhookDispatcher

            db = get_supabase_client(app.state.settings)
            if db is not None:
                dispatcher = WebhookDispatcher(db)
                await dispatcher.retry_failed()
        except Exception as e:
            logger.debug("Webhook retry loop error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from visionscore.config import Settings

    app.state.settings = Settings()
    task = asyncio.create_task(_webhook_retry_loop(app))
    yield
    task.cancel()


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
app.add_middleware(GZipMiddleware, minimum_size=500)

app.include_router(router, prefix="/api/v1")
