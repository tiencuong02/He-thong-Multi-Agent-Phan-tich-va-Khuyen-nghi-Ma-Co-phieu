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
            # Temporarily bypassed for frontend debugging without Docker
            # cls.producer = AIOKafkaProducer(
            #     bootstrap_servers=KAFKA_BROKER_URL,
            #     value_serializer=lambda v: json.dumps(v).encode('utf-8')
            # )
            # await cls.producer.start()
            logger.info("Kafka Producer bypassed for local testing")
        return cls.producer

    @classmethod
    async def stop_producer(cls):
        if cls.producer:
            await cls.producer.stop()
            logger.info("Kafka Producer stopped")

    @classmethod
    async def publish_message(cls, message: dict):
        producer = await cls.get_producer()
        try:
            await producer.send_and_wait(KAFKA_TOPIC, message)
            logger.info(f"Published message to {KAFKA_TOPIC}: {message.get('job_id')}")
        except Exception as e:
            logger.error(f"Failed to publish message to Kafka: {e}")
            raise
