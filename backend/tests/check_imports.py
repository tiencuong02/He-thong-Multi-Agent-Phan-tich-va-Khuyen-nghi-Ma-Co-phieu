import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Testing imports...")
try:
    from app.core.config import settings
    print("- Core Config imported.")
    from app.db.mongodb import db_instance
    print("- MongoDB imported.")
    from app.db.redis import redis_instance
    print("- Redis imported.")
    from app.api.kafka_producer import KafkaProducerService
    print("- Kafka Producer imported.")
    from app.models.stock import AnalysisResult
    print("- Models imported.")
    from app.repositories.report_repository import ReportRepository
    print("- Repositories imported.")
    from app.services.analysis_service import AnalysisService
    print("- Services imported.")
    from app.api.endpoints import router
    print("- Endpoints imported.")
    # from app.main import app  # Importing main might trigger lifespan/event loop issues in a script
    # print("- Main App imported.")
    print("\nAll imports successful!")
except Exception as e:
    print(f"\nImport failed: {str(e)}")
    import traceback
    traceback.print_exc()
