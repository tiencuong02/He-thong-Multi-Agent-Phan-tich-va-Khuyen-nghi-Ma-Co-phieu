import json
import logging
from aiokafka import AIOKafkaProducer
from app.core.config import settings

logger = logging.getLogger(__name__)

class KafkaProducerService:
    producer: AIOKafkaProducer = None

    @classmethod
    async def get_producer(cls) -> AIOKafkaProducer:
        if cls.producer is None:
            try:
                logger.info(f"Initializing Kafka Producer with broker: {settings.KAFKA_BROKER_URL}")
                cls.producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BROKER_URL,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    request_timeout_ms=5000
                )
                await cls.producer.start()
                logger.info("Kafka Producer started successfully.")
            except Exception as e:
                logger.error(f"Kafka connection failed: {e}. System will use background task fallback.")
                cls.producer = None
        return cls.producer

    @classmethod
    async def stop_producer(cls):
        if cls.producer:
            try:
                await cls.producer.stop()
                logger.info("Kafka Producer stopped.")
            except Exception as e:
                logger.error(f"Error stopping Kafka Producer: {e}")
            finally:
                cls.producer = None

    @classmethod
    async def publish_message(cls, message: dict) -> bool:
        try:
            producer = await cls.get_producer()
            if producer is None:
                return False
            await producer.send_and_wait(settings.KAFKA_TOPIC, message)
            logger.info(f"Published message to Kafka topic {settings.KAFKA_TOPIC}: {message.get('job_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to Kafka: {e}")
            return False
