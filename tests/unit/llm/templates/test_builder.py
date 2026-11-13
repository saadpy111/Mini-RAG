from src.enums import QuestionLanguage
from src.llm.templates import (
    PROMPT_TEMPLATES,
    PromptType,
    build_prompt_messages,
    build_rag_messages,
)


def get_template(language):
    return PROMPT_TEMPLATES[(PromptType.RAG_ANSWER, language)]


def test_english_system_instruction_requires_grounding():
    template = get_template(QuestionLanguage.ENGLISH)
    instruction = template.system_instruction.lower()

    assert "same language" in instruction
    assert "only the retrieved context" in instruction
    assert "never invent" in instruction
    assert "insufficient" in instruction


def test_arabic_system_instruction_requires_grounding():
    template = get_template(QuestionLanguage.ARABIC)
    instruction = template.system_instruction

    assert "نفس لغة سؤال المستخدم" in instruction
    assert "السياق المسترجع" in instruction
    assert "لا تختلق" in instruction
    assert "غير كافٍ" in instruction


def test_build_rag_messages_uses_english_template_and_context():
    template = get_template(QuestionLanguage.ENGLISH)

    messages = build_rag_messages(
        template,
        question="What is RAG?",
        context="[1] RAG combines retrieval with generation.",
    )

    assert [message.role for message in messages] == ["system", "user"]
    assert messages[0].content == template.system_instruction
    assert "What is RAG?" in messages[1].content
    assert "[1] RAG combines retrieval with generation." in messages[1].content


def test_build_rag_messages_uses_arabic_template_and_context():
    template = get_template(QuestionLanguage.ARABIC)

    messages = build_rag_messages(
        template,
        question="ما هو RAG؟",
        context="[1] يجمع RAG بين الاسترجاع والتوليد.",
    )

    assert messages[0].content == template.system_instruction
    assert "ما هو RAG؟" in messages[1].content
    assert "[1] يجمع RAG بين الاسترجاع والتوليد." in messages[1].content


def test_build_prompt_messages_formats_supplied_variables():
    template = get_template(QuestionLanguage.ENGLISH)

    messages = build_prompt_messages(
        template,
        {
            "question": "Custom question",
            "context": "Custom context",
        },
    )

    assert "Custom question" in messages[1].content
    assert "Custom context" in messages[1].content
