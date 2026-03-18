from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from app.api.endpoints import router as api_router
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.db.redis import connect_to_redis, close_redis_connection
from app.api.kafka_producer import KafkaProducerService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await connect_to_redis()
    await KafkaProducerService.get_producer()
    yield
    # Shutdown
    await close_mongo_connection()
    await close_redis_connection()
    await KafkaProducerService.stop_producer()

app = FastAPI(
    title="Multi-Agent Stock Analysis API",
    description="FastAPI backend powered by CrewAI for stock analysis.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for development. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Multi-Agent Stock Analysis API"}
