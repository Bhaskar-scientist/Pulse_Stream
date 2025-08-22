"""Main FastAPI application for PulseStream."""

import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from core.config import settings
from core.logging import configure_logging, get_logger
from core.errors import PulseStreamError


# Configure logging
logger = configure_logging(settings.log_level, settings.log_format)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting PulseStream application", version=settings.app_version)
    
    # TODO: Initialize database connection
    # TODO: Initialize Redis connection
    # TODO: Initialize background tasks
    
    yield
    
    # Shutdown
    logger.info("Shutting down PulseStream application")
    
    # TODO: Close database connections
    # TODO: Close Redis connections
    # TODO: Cleanup background tasks


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        description="Multi-tenant, real-time API monitoring and analytics platform",
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests."""
        start_time = time.time()
        
        # Log request
        logger.info(
            "HTTP request started",
            method=request.method,
            url=str(request.url),
            client=request.client.host if request.client else None,
        )
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                "HTTP request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=round(process_time, 4),
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "HTTP request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                process_time=round(process_time, 4),
            )
            raise
    
    # Exception handlers
    @app.exception_handler(PulseStreamError)
    async def pulse_stream_exception_handler(request: Request, exc: PulseStreamError):
        """Handle PulseStream custom exceptions."""
        logger.error(
            "PulseStream error",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            url=str(request.url),
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.error_code or "PULSE_STREAM_ERROR",
                "message": exc.message,
                "details": exc.details,
            },
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            url=str(request.url),
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            "Unexpected error",
            error=str(exc),
            type=type(exc).__name__,
            url=str(request.url),
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            },
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": time.time(),
            "environment": settings.environment,
        }
    
    # Root endpoint
    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": "Multi-tenant, real-time API monitoring and analytics platform",
            "docs_url": "/docs" if settings.debug else None,
            "health_url": "/health",
        }
    
    # Include routers
    from apps.auth.api import router as auth_router
    from apps.ingestion.api import router as ingestion_router
    from apps.alerting.api import router as alerting_router
    from apps.dashboard.api import router as dashboard_router
    
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(ingestion_router, prefix=settings.api_v1_prefix)
    app.include_router(alerting_router, prefix=settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
