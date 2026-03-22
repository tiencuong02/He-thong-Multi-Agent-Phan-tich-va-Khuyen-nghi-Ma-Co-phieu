import asyncio
import json
import logging
import os
import datetime
from aiokafka import AIOKafkaConsumer

# This needs to run independently of FastAPI, so we initialize connections
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_db
from app.db.redis import connect_to_redis, close_redis_connection
from app.db.cache_service import CacheService
from app.agents.crew import run_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "stock_analysis_tasks")

async def process_job(job_id: str, ticker: str):
    logger.info(f"[WORKER] Received job_id={job_id} ticker={ticker}")

    # ── 1. Duplicate-job guard ──────────────────────────────────────────────────
    # Check if this job was already processed (Kafka at-least-once delivery can
    # cause duplicate messages).
    try:
        existing = await CacheService.get("job", job_id)
        if existing and existing.get("status") in ("completed", "failed"):
            logger.info(f"[WORKER] job_id={job_id} already {existing['status']} — skipping duplicate")
            return
    except Exception:
        pass  # Redis unavailable → proceed normally

    # Mark as processing
    await CacheService.set("job", job_id, {
        "status": "processing",
        "ticker": ticker
    })

    try:
        # ── 2. Call Rule-Based Analysis ─────────────────────────────────────────
        logger.info(f"[RULE_ENGINE] Running analysis for ticker={ticker} | job_id={job_id}")
        result_dict = await run_analysis(ticker)
        logger.info(f"[RULE_ENGINE] Response received for ticker={ticker} | job_id={job_id}")

        report = {
            "ticker": ticker,
            "risk_opportunity": result_dict.get("risk_opportunity", "N/A"),
            "recommendation": result_dict.get("recommendation", "Hold"),
            "price": result_dict.get("price", 0),
            "trend": result_dict.get("trend", "stable"),
            "confidence": result_dict.get("confidence", 0.5),
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        # Save to DB
        db = get_db()
        if db is not None:
            await db["reports"].insert_one(report.copy())

        report.pop("_id", None)

        # Save to result cache (TTL 30 min)
        await CacheService.set("ai_result", ticker, report)

        # Update job state to completed
        await CacheService.set("job", job_id, {
            "status": "completed",
            "result": report
        })
        logger.info(f"[WORKER] job_id={job_id} completed successfully.")

    except Exception as e:
        error_str = str(e)
        logger.error(f"[WORKER] job_id={job_id} failed: {error_str}", exc_info=True)
        
        await CacheService.set("job", job_id, {
            "status": "failed",
            "error": error_str
        })


async def consume():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER_URL,
        group_id="stock_analysis_group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    retries = 20
    while retries > 0:
        try:
            await consumer.start()
            logger.info("Kafka Consumer started and connected.")
            break
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}. Retrying... ({retries} left)")
            retries -= 1
            await asyncio.sleep(5)
            
    if retries == 0:
        logger.error("Could not connect to Kafka. Exiting consumer.")
        return

    try:
        async for msg in consumer:
            data = msg.value
            job_id = data.get("job_id")
            ticker = data.get("ticker")
            
            if job_id and ticker:
                # We do not block the consumer loop, we create a task
                asyncio.create_task(process_job(job_id, ticker))
    finally:
        await consumer.stop()

async def main():
    logger.info("Starting worker service...")
    await connect_to_mongo()
    await connect_to_redis()
    
    try:
        await consume()
    except asyncio.CancelledError:
        logger.info("Worker stopped.")
    finally:
        await close_mongo_connection()
        await close_redis_connection()

if __name__ == "__main__":
    asyncio.run(main())
