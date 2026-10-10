"""
TruthLens AI — FastAPI Application Entry Point.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TruthLens AI",
        description="Evidence-Grounded Multimodal Claim Verification System",
        version="1.0.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(router)

    # Startup event
    @app.on_event("startup")
    async def on_startup():
        logger.info("Initializing database...")
        init_db()
        logger.info("TruthLens AI backend started.")
        logger.info(f"LLM configured: {settings.is_llm_configured}")
        logger.info(f"Search configured: {settings.is_search_configured}")

    return app


app = create_app()
