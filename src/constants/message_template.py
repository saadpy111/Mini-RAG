from enum import StrEnum


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
