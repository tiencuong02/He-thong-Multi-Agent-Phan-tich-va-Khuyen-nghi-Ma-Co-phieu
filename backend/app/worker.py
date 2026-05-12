import asyncio
import json
import logging
import signal
from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.db.mongodb import connect_to_mongo, get_db, close_mongo_connection
from app.db.redis import connect_to_redis, close_redis_connection
from app.api.kafka_producer import KafkaProducerService
from app.repositories.report_repository import ReportRepository
from app.repositories.job_repository import JobRepository
from app.services.analysis_service import AnalysisService

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Worker")

# Global graceful shutdown flag
shutdown_event = asyncio.Event()

def handle_exit(sig, frame):
    logger.info(f"Received exit signal {sig}...")
    shutdown_event.set()

async def consume_messages():
    """
    Main Kafka consumption loop using AnalysisService.
    """
    logger.info(f"Connecting to Kafka at {settings.KAFKA_BROKER_URL}...")

    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC,
        bootstrap_servers=settings.KAFKA_BROKER_URL,
        group_id="stock-analysis-workers",
        auto_offset_reset="earliest",
        session_timeout_ms=120000,   # 2 min — phân tích AI có thể mất 30-120s
        heartbeat_interval_ms=10000, # heartbeat mỗi 10s (< session_timeout/3)
        max_poll_interval_ms=300000, # 5 min max giữa 2 lần poll
    )

    max_kafka_retries = 15
    for attempt in range(1, max_kafka_retries + 1):
        try:
            await consumer.start()
            break
        except Exception as e:
            logger.warning(f"Kafka not ready (attempt {attempt}/{max_kafka_retries}): {e}, retrying in 5s...")
            if attempt == max_kafka_retries:
                logger.error("Failed to connect to Kafka after all retries. Exiting.")
                raise
            await asyncio.sleep(5)

    logger.info(f"Worker started. Listening on topic: {settings.KAFKA_TOPIC}")

    # Setup Infrastructure for Service — retry MongoDB connection
    max_retries = 10
    for attempt in range(1, max_retries + 1):
        await connect_to_mongo()
        db = get_db()
        if db is not None:
            logger.info(f"MongoDB connected on attempt {attempt}")
            break
        logger.warning(f"MongoDB not ready (attempt {attempt}/{max_retries}), retrying in 3s...")
        await asyncio.sleep(3)
    else:
        logger.error("Failed to connect to MongoDB after all retries. Exiting.")
        await consumer.stop()
        return

    await connect_to_redis()

    report_repo = ReportRepository(db)
    job_repo = JobRepository()
    kafka_producer = KafkaProducerService() # Actually worker doesn't need to publish back, but service needs it for init (logic can be split further but this is ok for now)
    
    service = AnalysisService(report_repo, job_repo, kafka_producer)

    try:
        while not shutdown_event.is_set():
            try:
                # Wait for 1.0s to allow checking shutdown_event
                msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
                data = json.loads(msg.value.decode("utf-8"))
                
                job_id = data.get("job_id")
                ticker = data.get("ticker")
                user_id = data.get("user_id")
                
                logger.info(f"[*] Processing job {job_id} for {ticker} (User: {user_id})")
                
                # Execute via Service
                await service.process_analysis_sync(job_id, ticker, user_id=user_id)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    finally:
        await consumer.stop()
        await close_mongo_connection()
        await close_redis_connection()
        logger.info("Worker stopped gracefully.")

if __name__ == "__main__":
    # Handle termination signals
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    asyncio.run(consume_messages())
