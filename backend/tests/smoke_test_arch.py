import sys
import os
import asyncio

# Ensure app is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def smoke_test():
    print("Starting Architecture Smoke Test...")
    try:
        from app.models.stock import AnalysisResult
        from app.repositories.report_repository import ReportRepository
        from app.services.analysis_service import AnalysisService
        
        print("✅ Models, Repositories, and Services imports successful.")
        
        # Mocking a collection for repo init
        class MockCollection:
            pass
        class MockDB:
            def __getitem__(self, name): return MockCollection()
            
        repo = ReportRepository(MockDB())
        print("✅ Repository instantiation successful.")
        
        # Mocking JobRepo and Kafka for Service init
        class MockJobRepo: pass
        class MockKafka: pass
        
        service = AnalysisService(repo, MockJobRepo(), MockKafka())
        print("✅ Service instantiation successful.")
        
        print("\n🚀 Smoke Test PASSED: The new layered architecture structure is valid.")
        
    except Exception as e:
        print(f"❌ Smoke Test FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(smoke_test())
