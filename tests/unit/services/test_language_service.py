import pytest

from src.enums import QuestionLanguage
from src.services.language_service import detect_question_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("What is retrieval augmented generation?", QuestionLanguage.ENGLISH),
        ("ما هو الاسترجاع المعزز؟", QuestionLanguage.ARABIC),
        ("ما هو RAG؟", QuestionLanguage.ARABIC),
        ("What is RAG ما هو؟", QuestionLanguage.ENGLISH),
        ("12345", QuestionLanguage.ENGLISH),
        ("؟،", QuestionLanguage.ENGLISH),
    ],
)
def test_detect_question_language(text, expected):
    assert detect_question_language(text) is expected
