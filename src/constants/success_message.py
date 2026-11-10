from enum import StrEnum


class SuccessMessage(StrEnum):
    """Static success messages returned to API clients."""

    OPERATION_COMPLETED = "Operation completed successfully."
    APPLICATION_INFO_RETRIEVED = (
        "Application information retrieved successfully."
    )
    PROJECT_CREATED = "Project created successfully."
    FILE_UPLOADED = "File uploaded and asset metadata saved successfully."
    FILE_PROCESSED = "File processed and chunks saved successfully."
    PROJECT_CHUNKS_DELETED = "Project chunks deleted successfully."
    VECTORS_INDEXED = "Project vectors indexed successfully."
    VECTOR_SEARCH_COMPLETED = "Vector search completed successfully."
    LLM_CHAT_TEST_COMPLETED = "LLM chat test completed successfully."
    LLM_EMBEDDING_TEST_COMPLETED = (
        "LLM embedding test completed successfully."
    )
