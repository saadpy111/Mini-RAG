from fastapi import FastAPI

from src.api import register_exception_handlers
from src.controllers import data_router
from src.routes.base import router

app = FastAPI()

register_exception_handlers(app)

app.include_router(data_router)
app.include_router(router)
