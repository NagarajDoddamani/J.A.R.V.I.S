from qdrant_client import AsyncQdrantClient

from backend.core.config import settings
from backend.core.logging import logger


class QdrantManager:
    def __init__(self):
        self.client = None

    async def connect(self):
        if self.client:
            return
        
        try:
            self.client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=10
            )
            logger.info("Qdrant connected", host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        except Exception as e:
            logger.error("Qdrant connection failed", error=str(e))
            raise

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Qdrant connection closed")

    async def is_healthy(self) -> bool:
        if not self.client:
            return False
        try:
            # Simple check, we can list collections or just ping if available
            # Listing collections as a proxy for health
            await self.client.get_collections()
            return True
        except Exception:
            return False

qdrant_manager = QdrantManager()

async def get_qdrant_client():
    return qdrant_manager.client
