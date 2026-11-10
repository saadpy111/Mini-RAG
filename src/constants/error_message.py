from enum import StrEnum


class ErrorMessage(StrEnum):
    """Static error messages returned to API clients or raised as
    application-owned validation/invariant errors."""

    # API infrastructure
    REQUEST_VALIDATION_FAILED = "Request validation failed."
    REQUEST_FAILED = "Request failed."
    INTERNAL_SERVER_ERROR = "An internal server error occurred."

    # Result pattern invariants
    SUCCESS_CANNOT_CONTAIN_ERROR = (
        "A successful result cannot contain an error."
    )
    FAILURE_REQUIRES_ERROR = "A failed result must contain an error."
    FAILURE_CANNOT_CONTAIN_VALUE = "A failed result cannot contain a value."

    # Projects
    PROJECT_NOT_FOUND = "Project not found."
    PROJECT_WAS_NOT_FOUND = "Project was not found."
    PROJECT_ALREADY_EXISTS = "A project with this ID already exists."
    INVALID_PROJECT_ID = "Invalid project ID."
    PROJECT_ID_MISSING = "Project identifier is missing."

    # Assets
    ASSET_NOT_FOUND = "Asset not found."
    ASSET_NOT_FOUND_FOR_FILE = "Asset not found for the specified file."
    INVALID_ASSET_ID = "Asset identifier is missing."
    INVALID_ASSET_NAME = "Asset name cannot be empty."
    ASSET_METADATA_MISSING = (
        "Asset metadata does not contain a valid file identifier."
    )

    # Uploads and files
    MISSING_FILENAME = "Filename is required."
    FILE_STORAGE_ERROR = "Failed to save the uploaded file."
    UPLOADED_FILE_SIZE_UNAVAILABLE = (
        "The uploaded file size could not be determined."
    )
    INVALID_FILE_ID = "Invalid file ID."
    FILE_LOOKUP_ERROR = "Failed to access the project files."
    FILE_READ_ERROR = "Failed to read the file content."
    INVALID_FILE_CONTENT_PARSED = "The file content could not be parsed."
    INVALID_FILE_CONTENT_PROCESSED = "The file content could not be processed."
    EMPTY_DOCUMENT_CONTENT = (
        "The file does not contain any processable content."
    )
    NO_CONTENT_TO_PROCESS = "No content found to process."

    # Chunk processing and persistence
    INVALID_CHUNK_SIZE = "chunk_size must be greater than zero."
    INVALID_OVERLAP_SIZE = "overlap_size cannot be negative."
    INVALID_CHUNK_CONFIGURATION = (
        "overlap_size must be smaller than chunk_size."
    )
    NO_CHUNKS_GENERATED = "No chunks were generated from the file."
    EMPTY_CHUNKS = "Chunks list cannot be empty."
    INVALID_BATCH_SIZE = "Batch size must be greater than zero."
    INVALID_BATCH_SIZE_GUARD = "batch_size must be greater than zero"
    PROJECT_ID_MISMATCH = "All chunks must belong to the same project."
    ASSET_ID_MISMATCH = "All chunks must belong to the same asset."
    CHUNK_SCOPE_MISMATCH = (
        "All chunks must belong to the specified project and asset."
    )
    CHUNK_PERSISTENCE_FAILED = "Chunks could not be persisted."
    CHUNK_LOOKUP_FAILED = "Existing chunks could not be retrieved."
    CHUNK_NOT_FOUND = "Chunk not found."
    NO_CHUNKS_TO_INDEX = "Project has no chunks to index."

    # Project-level processing
    NO_ASSETS_IN_PROJECT = "Project has no assets to process."

    # LLM integration
    LLM_PROVIDER_UNSUPPORTED = "The configured LLM provider is not supported."
    LLM_MODEL_NOT_APPROVED = (
        "The requested model is not approved for this operation."
    )
    LLM_API_KEY_MISSING = "The LLM provider API key is not configured."
    LLM_AUTH_FAILED = (
        "The LLM provider rejected the configured credentials."
    )
    LLM_RATE_LIMITED = (
        "The LLM provider rate limit was exceeded. Try again later."
    )
    LLM_TIMEOUT = "The LLM provider request timed out."
    LLM_PROVIDER_ERROR = "The LLM provider request failed."
    LLM_INVALID_RESPONSE = (
        "The LLM provider returned an unexpected response."
    )
    EMPTY_EMBEDDING_INPUT = "Embedding input cannot be empty."
    INVALID_CHAT_MESSAGES = "Chat messages are missing or invalid."
    LLM_TEST_ENDPOINTS_DISABLED = "LLM diagnostic endpoints are disabled."

    # Vector database
    VECTOR_DB_PROVIDER_UNSUPPORTED = (
        "The configured vector database provider is not supported."
    )
    VECTOR_DB_CONFIGURATION_INVALID = (
        "The vector database configuration is invalid."
    )
    VECTOR_DB_CONNECTION_FAILED = "The vector database connection failed."
    VECTOR_DB_COLLECTION_INITIALIZATION_FAILED = (
        "The vector database collection could not be initialized."
    )
    VECTOR_DB_COLLECTION_MISMATCH = (
        "The vector database collection configuration does not match "
        "the application configuration."
    )
    VECTOR_DB_COLLECTION_NOT_CONFIGURED = (
        "The requested vector database collection is not configured."
    )
    VECTOR_DB_INVALID_VECTOR_ID = "The vector ID is not valid."
    VECTOR_DB_INVALID_VECTOR_DIMENSION = (
        "The vector dimension does not match the collection configuration."
    )
    VECTOR_DB_INVALID_PAYLOAD = (
        "Vector metadata must include a non-empty project ID."
    )
    VECTOR_DB_INVALID_PROJECT_FILTER = (
        "A non-empty project ID is required for this vector operation."
    )
    VECTOR_DB_INVALID_SEARCH_LIMIT = "Search limit must be greater than zero."
    VECTOR_DB_UPSERT_FAILED = "The vectors could not be stored."
    VECTOR_DB_SEARCH_FAILED = "The vector search failed."
    VECTOR_DB_DELETE_FAILED = "The vectors could not be deleted."
    VECTOR_DB_PROJECT_VECTOR_LOOKUP_FAILED = (
        "The project vectors could not be retrieved."
    )
    EMPTY_SEARCH_QUERY = "Search query cannot be empty."

    # Pagination
    INVALID_PAGINATION = (
        "Page size and page number must be greater than zero."
    )
    PAGE_SIZE_TOO_LARGE = "Page size cannot exceed 100."
    INVALID_PAGE_SIZE_GUARD = "page_size must be greater than zero"
    INVALID_PAGE_NUM_GUARD = "page_num must be greater than zero"

    # Chunks
    INVALID_CHUNK_ID = "Invalid chunk ID."
