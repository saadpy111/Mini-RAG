from fastapi import FastAPI
from src.api import register_exception_handlers
from src.routes import data_router , base_router

from src.db.mongodb import lifespan
app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)

app.include_router(base_router)
app.include_router(data_router)
