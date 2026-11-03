"""Provider-agnostic chat-completion contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from src.helpers.result_pattern import Result


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatCompletionOutput:
    content: str
    model: str


class ChatProvider(ABC):
    """Contract for chat-completion integrations."""

    model_id: str

    @abstractmethod
    async def complete(
        self,
        messages: Sequence[ChatMessage],
    ) -> Result[ChatCompletionOutput]:
        """Return one assistant completion for ``messages``."""
