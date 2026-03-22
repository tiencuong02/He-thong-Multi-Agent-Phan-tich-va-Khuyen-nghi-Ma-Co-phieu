import json
import logging
from aiokafka import AIOKafkaProducer
import os

KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "stock_analysis_tasks")

logger = logging.getLogger(__name__)

class KafkaProducerService:
    producer = None

    @classmethod
    async def get_producer(cls):
        if cls.producer is None:
            try:
                cls.producer = AIOKafkaProducer(
                    bootstrap_servers=KAFKA_BROKER_URL,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    request_timeout_ms=5000 # Short timeout for startup
                )
                await cls.producer.start()
                logger.info("Kafka Producer started successfully")
            except Exception as e:
                logger.error(f"Kafka startup failed: {e}. App will continue without Kafka producer.")
                cls.producer = None
        return cls.producer

    @classmethod
    async def stop_producer(cls):
        if cls.producer:
            try:
                await cls.producer.stop()
                logger.info("Kafka Producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka Producer: {e}")
            finally:
                cls.producer = None

    @classmethod
    async def publish_message(cls, message: dict) -> bool:
        producer = await cls.get_producer()
        if producer is None:
            logger.warning(f"Kafka producer not available. Skipping message: {message.get('job_id')}")
            return False
            
        try:
            await producer.send_and_wait(KAFKA_TOPIC, message)
            logger.info(f"Published message to {KAFKA_TOPIC}: {message.get('job_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to Kafka: {e}")
            return False
