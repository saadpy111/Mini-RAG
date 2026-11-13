"""Prompt message construction for LLM providers."""

from collections.abc import Mapping
from typing import Any

from src.llm.contracts import ChatMessage
from src.llm.templates.types import PromptTemplate


def build_prompt_messages(
    template: PromptTemplate,
    variables: Mapping[str, Any],
) -> list[ChatMessage]:
    """Render a template into provider-agnostic chat messages."""

    return [
        ChatMessage(
            role="system",
            content=template.system_instruction,
        ),
        ChatMessage(
            role="user",
            content=template.user_instruction_template.format(**variables),
        ),
    ]


def build_rag_messages(
    template: PromptTemplate,
    question: str,
    context: str,
) -> list[ChatMessage]:
    """Render a RAG template with the question and grounded context."""

    return build_prompt_messages(
        template,
        {
            "question": question,
            "context": context,
        },
    )
