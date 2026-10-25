from contextlib import asynccontextmanager
from .indexes import create_indexes
from fastapi import FastAPI
from  pymongo import AsyncMongoClient

from src.helpers.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    
    client = AsyncMongoClient(settings.mongodb_uri)

    try:
        await client.admin.command("ping")

        app.state.mongodb_client = client
        app.state.mongodb = client[settings.mongodb_database]
        await create_indexes(app.state.mongodb)

        yield

    finally:
        await client.close()