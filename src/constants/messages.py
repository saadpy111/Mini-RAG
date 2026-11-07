
from enum import StrEnum


class ErrorCode(StrEnum):
    """Stable machine-readable codes returned in API errors."""

    # Result pattern fallback
    FALLBACK = "error"

    # Projects
    PROJECT_NOT_FOUND = "project_not_found"
    PROJECT_ALREADY_EXISTS = "project_already_exists"
    INVALID_PROJECT_ID = "invalid_project_id"

    # Assets
    ASSET_NOT_FOUND = "asset_not_found"
    INVALID_ASSET_ID = "invalid_asset_id"
    INVALID_ASSET_NAME = "invalid_asset_name"
    ASSET_METADATA_MISSING = "asset_metadata_missing"
    ASSET_ID_MISMATCH = "asset_id_mismatch"

    # Uploads and files
    MISSING_FILENAME = "missing_filename"
    FILE_TOO_LARGE = "file_too_large"
    FILE_STORAGE_ERROR = "file_storage_error"
    UPLOADED_FILE_SIZE_UNAVAILABLE = "uploaded_file_size_unavailable"
    INVALID_FILE_ID = "invalid_file_id"
    FILE_LOOKUP_ERROR = "file_lookup_error"
    FILE_NOT_FOUND = "file_not_found"
    FILE_READ_ERROR = "file_read_error"
    INVALID_FILE_CONTENT = "invalid_file_content"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    EMPTY_DOCUMENT_CONTENT = "empty_document_content"

    # Chunk processing and persistence
    INVALID_CHUNK_SIZE = "invalid_chunk_size"
    INVALID_OVERLAP_SIZE = "invalid_overlap_size"
    INVALID_CHUNK_CONFIGURATION = "invalid_chunk_configuration"
    NO_CHUNKS_GENERATED = "no_chunks_generated"
    EMPTY_CHUNKS = "empty_chunks"
    INVALID_BATCH_SIZE = "invalid_batch_size"
    PROJECT_ID_MISMATCH = "project_id_mismatch"
    CHUNK_SCOPE_MISMATCH = "chunk_scope_mismatch"
    CHUNK_PERSISTENCE_FAILED = "chunk_persistence_failed"
    CHUNK_LOOKUP_FAILED = "chunk_lookup_failed"
    CHUNK_CLEANUP_FAILED = "chunk_cleanup_failed"
    CHUNK_NOT_FOUND = "chunk_not_found"
    INVALID_CHUNK_ID = "invalid_chunk_id"

    # Project-level processing
    NO_ASSETS_IN_PROJECT = "no_assets_in_project"

    # LLM integration
    LLM_PROVIDER_UNSUPPORTED = "llm_provider_unsupported"
    LLM_MODEL_NOT_APPROVED = "llm_model_not_approved"
    LLM_API_KEY_MISSING = "llm_api_key_missing"
    LLM_AUTH_FAILED = "llm_auth_failed"
    LLM_RATE_LIMITED = "llm_rate_limited"
    LLM_TIMEOUT = "llm_timeout"
    LLM_PROVIDER_ERROR = "llm_provider_error"
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    EMPTY_EMBEDDING_INPUT = "empty_embedding_input"
    INVALID_CHAT_MESSAGES = "invalid_chat_messages"
    LLM_TEST_ENDPOINTS_DISABLED = "llm_test_endpoints_disabled"

    # Vector database
    VECTOR_DB_PROVIDER_UNSUPPORTED = "vector_db_provider_unsupported"
    VECTOR_DB_CONFIGURATION_INVALID = "vector_db_configuration_invalid"
    VECTOR_DB_CONNECTION_FAILED = "vector_db_connection_failed"
    VECTOR_DB_COLLECTION_INITIALIZATION_FAILED = (
        "vector_db_collection_initialization_failed"
    )
    VECTOR_DB_COLLECTION_MISMATCH = "vector_db_collection_mismatch"
    VECTOR_DB_COLLECTION_NOT_CONFIGURED = "vector_db_collection_not_configured"
    VECTOR_DB_INVALID_VECTOR_ID = "vector_db_invalid_vector_id"
    VECTOR_DB_INVALID_VECTOR_DIMENSION = "vector_db_invalid_vector_dimension"
    VECTOR_DB_INVALID_PAYLOAD = "vector_db_invalid_payload"
    VECTOR_DB_INVALID_PROJECT_FILTER = "vector_db_invalid_project_filter"
    VECTOR_DB_INVALID_SEARCH_LIMIT = "vector_db_invalid_search_limit"
    VECTOR_DB_UPSERT_FAILED = "vector_db_upsert_failed"
    VECTOR_DB_SEARCH_FAILED = "vector_db_search_failed"
    VECTOR_DB_DELETE_FAILED = "vector_db_delete_failed"

    # Pagination
    INVALID_PAGINATION = "invalid_pagination"
    PAGE_SIZE_TOO_LARGE = "page_size_too_large"


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
    LLM_CHAT_TEST_COMPLETED = "LLM chat test completed successfully."
    LLM_EMBEDDING_TEST_COMPLETED = (
        "LLM embedding test completed successfully."
    )


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

    # Pagination
    INVALID_PAGINATION = (
        "Page size and page number must be greater than zero."
    )
    PAGE_SIZE_TOO_LARGE = "Page size cannot exceed 100."
    INVALID_PAGE_SIZE_GUARD = "page_size must be greater than zero"
    INVALID_PAGE_NUM_GUARD = "page_num must be greater than zero"

    # Chunks
    INVALID_CHUNK_ID = "Invalid chunk ID."


class MessageTemplate(StrEnum):
    """Message templates that preserve runtime details when formatted."""

    PROJECT_NOT_FOUND = "Project '{project_id}' was not found."
    FILE_NOT_FOUND = (
        "File '{file_id}' was not found in project '{project_id}'."
    )
    UNSUPPORTED_FILE_TYPE = "Unsupported file type: {extension}."
    ALLOWED_FILE_TYPES = (
        "File type not allowed. Allowed types: {allowed_types}"
    )
    FILE_TOO_LARGE = "File size exceeds the limit of {max_size} MB."
    PROJECT_PROCESS_SUMMARY = (
        "Processed {processed_assets} of {total_assets} asset(s); "
        "{total_chunks} chunk(s) saved; {failed_assets} failed."
    )
    ASSET_FAILURE_SUMMARY = "{message} ({remaining} more asset(s) failed.)"
    CHUNK_CLEANUP_FAILED = (
        "{inserted_count} replacement chunks were stored, but the previous "
        "chunks could not be removed; old chunks may remain."
    )
    CHUNK_CLEANUP_PARTIAL = (
        "{inserted_count} replacement chunks were stored, but only "
        "{deleted_count} of {expected_count} previous chunks were removed; "
        "old chunks may remain."
    )

    # Vector database
    VECTOR_DB_COLLECTION_NOT_CONFIGURED = (
        "Vector collection '{collection_name}' is not configured."
    )
    VECTOR_DB_COLLECTION_DIMENSION_MISMATCH = (
        "Vector collection '{collection_name}' has dimension {actual}, "
        "expected {expected}."
    )
    VECTOR_DB_COLLECTION_DISTANCE_MISMATCH = (
        "Vector collection '{collection_name}' uses distance '{actual}', "
        "expected '{expected}'."
    )
    VECTOR_DB_COLLECTION_LAYOUT_UNSUPPORTED = (
        "Vector collection '{collection_name}' does not use a single "
        "unnamed vector configuration."
    )
    VECTOR_DB_INVALID_VECTOR_DIMENSION = (
        "Vector dimension {actual} does not match collection "
        "'{collection_name}' dimension {expected}."
    )
    VECTOR_DB_INVALID_VECTOR_ID = (
        "Vector ID '{vector_id}' is not a valid UUID."
    )
    VECTOR_DB_DUPLICATE_COLLECTION = (
        "Vector collection name '{collection_name}' is configured more "
        "than once."
    )
