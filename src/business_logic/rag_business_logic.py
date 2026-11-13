"""Application use case for grounded RAG question answering."""

from src.business_logic.vector_business_logic import VectorBusinessLogic
from src.dtos import RAGAnswerResultDTO
from src.helpers.result_pattern import Result
from src.llm.factories import ChatProviderFactory
from src.llm.templates import (
    PromptType,
    build_rag_messages,
    get_prompt_template,
)
from src.services.language_service import detect_question_language
from src.services.rag_context_service import build_grounded_context
from src.validators.rag_validator import (
    validate_rag_project_id,
    validate_rag_question,
)


DEFAULT_CONTEXT_LIMIT = 5


class RAGBusinessLogic:
    """Orchestrate retrieval, prompt selection, and LLM completion."""

    def __init__(
        self,
        vector_business_logic: VectorBusinessLogic,
        chat_factory: ChatProviderFactory,
        context_limit: int = DEFAULT_CONTEXT_LIMIT,
    ):
        self.vector_business_logic = vector_business_logic
        self.chat_factory = chat_factory
        self.context_limit = context_limit

    async def answer_question(
        self,
        project_id: str,
        question: str,
    ) -> Result[RAGAnswerResultDTO]:
        question_result = validate_rag_question(question)

        if not question_result.is_success:
            return Result.failure(question_result.error)

        project_result = validate_rag_project_id(project_id)

        if not project_result.is_success:
            return Result.failure(project_result.error)

        normalized_question = question_result.value
        normalized_project_id = project_result.value

        language = detect_question_language(normalized_question)

        retrieval_result = await self.vector_business_logic.search_project(
            project_id=normalized_project_id,
            query=normalized_question,
            limit=self.context_limit,
        )

        if not retrieval_result.is_success:
            return Result.failure(retrieval_result.error)

        context_result = build_grounded_context(
            retrieval_result.value or []
        )

        if not context_result.is_success:
            return Result.failure(context_result.error)

        template_result = get_prompt_template(
            language,
            PromptType.RAG_ANSWER,
        )

        if not template_result.is_success:
            return Result.failure(template_result.error)

        provider_result = self.chat_factory.create()

        if not provider_result.is_success:
            return Result.failure(provider_result.error)

        completion_result = await provider_result.value.complete(
            build_rag_messages(
                template_result.value,
                normalized_question,
                context_result.value.text,
            )
        )

        if not completion_result.is_success:
            return Result.failure(completion_result.error)

        return Result.success(
            RAGAnswerResultDTO(
                project_id=normalized_project_id,
                question=normalized_question,
                answer=completion_result.value.content,
                language=language,
                model=provider_result.value.model_id,
                sources=context_result.value.sources,
            )
        )
