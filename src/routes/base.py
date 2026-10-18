import os
from fastapi import APIRouter 
router = APIRouter(
    prefix = "/api/v1",
    tags=["api_v1"]
 )
@router.get("/")
async def read_root():
    return {
        "APP_NAME": os.getenv("APP_NAME"),
        "APP_VERSION" : os.getenv("APP_VERSION")
    }  


