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
