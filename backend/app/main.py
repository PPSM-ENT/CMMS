"""
CMMS API - Main Application Entry Point
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db, async_session_maker
from app.api.v1.router import api_router
from app.services.pm_scheduler import run_pm_scheduler

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    """
    # Startup
    logger.info("Starting CMMS API...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start PM scheduler in background
    scheduler_task = asyncio.create_task(run_pm_scheduler(async_session_maker))
    logger.info("PM scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down CMMS API...")
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## CMMS - Computerized Maintenance Management System

    Enterprise-grade maintenance management API with:

    * **Asset Management** - Hierarchical asset registry with specifications and meters
    * **Work Order Management** - Full lifecycle with status workflows
    * **Preventive Maintenance** - Time, meter, and condition-based scheduling
    * **Inventory Management** - Parts, storerooms, and purchase orders
    * **Reporting** - Dashboard metrics, MTBF/MTTR, PM compliance

    ### Authentication

    Use JWT tokens or API keys for authentication.
    - POST /api/v1/auth/login - Get JWT tokens
    - Include `Authorization: Bearer <token>` header
    - Or include `X-API-Key: <key>` header
    """,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/api/docs",
        "openapi_url": "/api/v1/openapi.json",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
