from pydantic import BaseModel

class UploadFileDTO(BaseModel):
    original_filename: str
    stored_filename: str
    file_id:str
    file_path: str
