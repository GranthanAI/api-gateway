import httpx
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.logging import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the sharedAsyncClient with pooling enabled (maximum 100 concurrent connections)
    logger.info("Initializing gateway shared HTTPX AsyncClient connection pool...")
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=150)
    app.state.client = httpx.AsyncClient(limits=limits, timeout=60.0)
    
    yield
    
    logger.info("Closing gateway shared HTTPX AsyncClient connection pool...")
    await app.state.client.aclose()
    logger.info("Gateway AsyncClient shut down successfully.")
