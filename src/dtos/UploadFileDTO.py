from pydantic import BaseModel

class UploadFileDTO(BaseModel):
    original_filename: str
    stored_filename: str
    file_path: str
