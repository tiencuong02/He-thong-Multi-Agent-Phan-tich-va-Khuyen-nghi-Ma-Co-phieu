from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Agent Stock Analysis Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"]
    
    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017/stockdb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Kafka
    KAFKA_BROKER_URL: str = "localhost:9092"
    KAFKA_TOPIC: str = "stock_analysis_tasks"
    
    # Backend Security
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_DONT_USE_THIS_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080 # 7 days
    
    # Default User passwords for DB Seeding
    ADMIN_PASSWORD: str = "admin"
    USER_PASSWORD: str = "123456"

    # External APIs
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # RAG Configuration
    OPENAI_API_KEY: Optional[str] = None    # RAG Settings
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "stock-reports-free")
    EMBEDDING_DIMENSION: int = 384  # paraphrase-multilingual-MiniLM-L12-v2
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()
