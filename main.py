from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api import register_exception_handlers
from src.db.mongodb import lifespan as mongodb_lifespan
from src.llm.lifecycle import llm_lifespan
from src.routes import (
    base_router,
    data_router,
    llm_router,
    vector_router,
)
from src.vector_db.VectorDBLifecycle import vector_db_lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mongodb_lifespan(app):
        async with llm_lifespan(app):
            async with vector_db_lifespan(app):
                yield


app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)

app.include_router(base_router)
app.include_router(data_router)
app.include_router(llm_router)
app.include_router(vector_router)
