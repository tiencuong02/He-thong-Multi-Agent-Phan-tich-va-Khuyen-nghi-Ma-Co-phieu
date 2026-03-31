from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Agent Stock Analysis Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017/stockdb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Kafka
    KAFKA_BROKER_URL: str = "localhost:9092"
    KAFKA_TOPIC: str = "stock_analysis_tasks"
    
    # External APIs
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    
    # RAG Configuration
    OPENAI_API_KEY: Optional[str]    # RAG Settings
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "stock-reports-free")
    EMBEDDING_DIMENSION: int = 384  # paraphrase-multilingual-MiniLM-L12-v2
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()
