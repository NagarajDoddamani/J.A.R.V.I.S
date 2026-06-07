import nats
from nats.js import JetStreamContext
from backend.core.config import settings
from backend.core.logging import logger

class NatsManager:
    def __init__(self):
        self.nc = None
        self.js = None

    async def connect(self):
        if self.nc is not None and self.nc.is_connected:
            return
        
        try:
            self.nc = await nats.connect(
                settings.NATS_URL,
                connect_timeout=10,
                reconnect_time_wait=2,
                max_reconnect_attempts=60,
                name=f"{settings.PROJECT_NAME}-backend"
            )
            self.js = self.nc.jetstream()
            logger.info("NATS connected", url=settings.NATS_URL)
            
            # Initialize JetStream (Governance FIX-07)
            await self._init_jetstream()
            
        except Exception as e:
            logger.error("NATS connection failed", error=str(e))
            raise

    async def _init_jetstream(self):
        # Implementation of streams as per governance (FIX-07)
        # We ensure a default stream exists for durable events
        try:
            stream_config = {
                "name": f"{settings.PROJECT_NAME}_EVENTS",
                "subjects": ["events.>"],
                "retention": settings.NATS_STREAM_RETENTION,
                "storage": settings.NATS_STREAM_STORAGE,
                "num_replicas": settings.NATS_STREAM_REPLICAS,
                "max_msg_size": settings.NATS_MAX_PAYLOAD,
            }
            # Add or update stream
            await self.js.add_stream(**stream_config)
            logger.info("NATS JetStream initialized with governance", stream=stream_config["name"])
        except Exception as e:
            logger.warning("NATS JetStream stream initialization skipped/failed", error=str(e))

    async def close(self):
        if self.nc:
            await self.nc.close()
            logger.info("NATS connection closed")

    async def is_healthy(self) -> bool:
        return self.nc is not None and self.nc.is_connected

nats_manager = NatsManager()

async def get_nats_client():
    return nats_manager.nc

async def get_jetstream_context():
    return nats_manager.js
