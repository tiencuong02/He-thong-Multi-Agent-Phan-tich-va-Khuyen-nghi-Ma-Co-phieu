import sys
import os
import time

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_import(module_path):
    print(f"Importing {module_path}...", end=" ", flush=True)
    start = time.time()
    try:
        __import__(module_path)
        print(f"SUCCESS ({time.time() - start:.2f}s)")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

print("Granular Import Test:")
test_import("app.core.config")
test_import("app.db.redis")
test_import("app.db.mongodb")
test_import("app.db.cache_service")
test_import("app.api.kafka_producer")
test_import("app.models.stock")
test_import("app.repositories.job_repository")
test_import("app.repositories.report_repository")
test_import("app.services.alpha_vantage")
test_import("app.agents.tools.browser_tool")
test_import("app.agents.market_researcher")
test_import("app.agents.financial_analyst")
test_import("app.agents.investment_advisor")
test_import("app.agents.crew")
test_import("app.services.analysis_service")
test_import("app.api.endpoints")
test_import("app.main")
print("\nTest finished.")
