from typing import AsyncGenerator
from backend.core.nats import nats_manager
from backend.core.redis import redis_manager
from backend.core.qdrant import qdrant_manager

async def get_nats_client():
    return nats_manager.nc

async def get_jetstream():
    return nats_manager.js

async def get_redis():
    return redis_manager.client

async def get_qdrant():
    return qdrant_manager.client
