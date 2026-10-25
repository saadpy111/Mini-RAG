
from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase


def get_database(request: Request) -> AsyncDatabase:
    return request.app.state.mongodb
