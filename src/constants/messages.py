
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
