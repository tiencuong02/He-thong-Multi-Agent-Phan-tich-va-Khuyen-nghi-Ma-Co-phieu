from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging

from app.core.config import settings
from app.api.router import router as api_router
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_db
from app.db.redis import connect_to_redis, close_redis_connection
from app.api.kafka_producer import KafkaProducerService

# Basic logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up services...")
    
    # Mongo
    try:
        await asyncio.wait_for(connect_to_mongo(), timeout=10.0)
    except Exception as e:
        logger.error(f"MongoDB startup failed: {e}")
        
    # Redis
    try:
        await asyncio.wait_for(connect_to_redis(), timeout=10.0)
    except Exception as e:
        logger.error(f"Redis startup failed: {e}")
        
    # Kafka
    try:
        await asyncio.wait_for(KafkaProducerService.get_producer(), timeout=10.0)
    except Exception as e:
        logger.warning(f"Kafka connection skipped during startup: {e}")
    
    # Initialize Data
    try:
        from app.repositories.user_repository import UserRepository
        from app.repositories.quote_repository import QuoteRepository
        from app.services.quote_service import QuoteService
        db = get_db()
        if db is not None:
            user_repo = UserRepository(db)
            await user_repo.init_default_users()
            
            quote_repo = QuoteRepository(db)
            quote_service = QuoteService(quote_repo)
            await quote_service.seed_quotes()
            logger.info("Default users and quotes initialized.")
    except Exception as e:
        logger.error(f"Data initialization failed: {e}")

    # RAG Services (singleton - load embedding model 1 lần duy nhất)
    try:
        from app.services.rag.vector_store import VectorStoreService
        from app.services.rag.rag_pipeline import RAGPipelineService
        logger.info("Initializing RAG services (singleton)...")
        app.state.vector_store = VectorStoreService()
        app.state.rag_pipeline = RAGPipelineService(app.state.vector_store)
        app.state.rag_pipeline._prewarm()
        logger.info("RAG services initialized successfully.")
    except Exception as e:
        logger.warning(f"RAG services initialization skipped: {e}")
        app.state.vector_store = None
        app.state.rag_pipeline = None

    logger.info("All services startup complete.")
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    await close_mongo_connection()
    await close_redis_connection()
    await KafkaProducerService.stop_producer()

from app.core.exceptions.app_exceptions import (
    BaseAppException, 
    app_exception_handler, 
    generic_exception_handler
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade Multi-Agent Stock Analysis API",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=True
)

# Exception Handlers
app.add_exception_handler(BaseAppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs"
    }

import datetime

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
