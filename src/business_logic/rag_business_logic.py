"""Application use case for grounded RAG question answering."""

from src.business_logic.vector_business_logic import VectorBusinessLogic
from src.constants import ErrorCode
from src.dtos import RAGAnswerResultDTO
from src.helpers.result_pattern import Result
from src.llm.factories import ChatProviderFactory
from src.observability.metrics import (
    RAG_ANSWERS_GENERATED_TOTAL,
    RAG_ERRORS_TOTAL,
    RAG_LLM_DURATION_SECONDS,
    RAG_NO_RELEVANT_CHUNKS_TOTAL,
    RAG_PIPELINE_DURATION_SECONDS,
    RAG_QUESTIONS_TOTAL,
    track_duration,
)
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

    @track_duration(RAG_PIPELINE_DURATION_SECONDS)
    async def answer_question(
        self,
        project_id: str,
        question: str,
    ) -> Result[RAGAnswerResultDTO]:
        question_result = validate_rag_question(question)

        if not question_result.is_success:
            RAG_ERRORS_TOTAL.labels(stage="validation").inc()
            return Result.failure(question_result.error)

        project_result = validate_rag_project_id(project_id)

        if not project_result.is_success:
            RAG_ERRORS_TOTAL.labels(stage="validation").inc()
            return Result.failure(project_result.error)

        normalized_question = question_result.value
        normalized_project_id = project_result.value

        language = detect_question_language(normalized_question)
        RAG_QUESTIONS_TOTAL.labels(language=language.value).inc()

        retrieval_result = await self.vector_business_logic.search_project(
            project_id=normalized_project_id,
            query=normalized_question,
            limit=self.context_limit,
        )

        if not retrieval_result.is_success:
            RAG_ERRORS_TOTAL.labels(stage="vector_search").inc()
            return Result.failure(retrieval_result.error)

        context_result = build_grounded_context(
            retrieval_result.value or []
        )

        if not context_result.is_success:
            if context_result.error.code == ErrorCode.NO_RELEVANT_CHUNKS:
                RAG_NO_RELEVANT_CHUNKS_TOTAL.labels(
                    language=language.value
                ).inc()
            else:
                RAG_ERRORS_TOTAL.labels(stage="context").inc()

            return Result.failure(context_result.error)

        template_result = get_prompt_template(
            language,
            PromptType.RAG_ANSWER,
        )

        if not template_result.is_success:
            RAG_ERRORS_TOTAL.labels(stage="prompt").inc()
            return Result.failure(template_result.error)

        provider_result = self.chat_factory.create()

        if not provider_result.is_success:
            RAG_ERRORS_TOTAL.labels(stage="llm").inc()
            return Result.failure(provider_result.error)

        with RAG_LLM_DURATION_SECONDS.time():
            completion_result = await provider_result.value.complete(
                build_rag_messages(
                    template_result.value,
                    normalized_question,
                    context_result.value.text,
                )
            )

        if not completion_result.is_success:
            RAG_ERRORS_TOTAL.labels(stage="llm").inc()
            return Result.failure(completion_result.error)

        RAG_ANSWERS_GENERATED_TOTAL.labels(
            language=language.value
        ).inc()

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
