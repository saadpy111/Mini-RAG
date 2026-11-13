"""Question language detection for prompt template selection."""

from src.enums import QuestionLanguage


ARABIC_LETTER_RANGES = (
    ("\u0600", "\u06FF"),
    ("\u0750", "\u077F"),
    ("\u08A0", "\u08FF"),
    ("\uFB50", "\uFDFF"),
    ("\uFE70", "\uFEFF"),
)


def _is_arabic_letter(character: str) -> bool:
    if not character.isalpha():
        return False

    return any(
        start <= character <= end
        for start, end in ARABIC_LETTER_RANGES
    )


def _is_latin_letter(character: str) -> bool:
    return character.isascii() and character.isalpha()


def detect_question_language(text: str) -> QuestionLanguage:
    """Return the dominant letter script used by ``text``.

    Questions containing Arabic letters without Latin letters are Arabic.
    Text without letters falls back to English, which is the application's
    default language.
    """

    arabic_letters = sum(
        1 for character in text if _is_arabic_letter(character)
    )
    latin_letters = sum(
        1 for character in text if _is_latin_letter(character)
    )

    if arabic_letters == 0:
        return QuestionLanguage.ENGLISH

    if latin_letters == 0:
        return QuestionLanguage.ARABIC

    if arabic_letters >= latin_letters:
        return QuestionLanguage.ARABIC

    return QuestionLanguage.ENGLISH
