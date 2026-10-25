from fastapi import FastAPI
from src.api import register_exception_handlers
from src.controllers import data_router
from src.routes.base import router
from src.db.mongodb import lifespan
app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)

app.include_router(router)
app.include_router(data_router)
