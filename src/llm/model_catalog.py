"""Default models and allowlists for the diagnostic LLM endpoints."""

DEFAULT_CHAT_MODEL = "nvidia/nemotron-3.5-lightning:free"
DEFAULT_EMBEDDING_MODEL = "nvidia/nemotron-3.5-embed-1b:free"

APPROVED_CHAT_MODELS: frozenset[str] = frozenset(
    {
        DEFAULT_CHAT_MODEL,
        "liquid/lfm-2.5-2.6b:free",
    }
)

APPROVED_EMBEDDING_MODELS: frozenset[str] = frozenset(
    {
        DEFAULT_EMBEDDING_MODEL,
        "liquid/lfm-2.5-embedding-350m:free",
    }
)
