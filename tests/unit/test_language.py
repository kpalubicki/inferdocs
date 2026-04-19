"""Unit tests for language detection."""

from app.services.documents.language import detect_language


class TestDetectLanguage:
    def test_latin_text_returns_english(self) -> None:
        text = "The quick brown fox jumps over the lazy dog. " * 5
        assert detect_language(text) == "English"

    def test_cyrillic_text_returns_russian(self) -> None:
        text = "Это тестовый текст на русском языке для проверки обнаружения языка. " * 3
        assert detect_language(text) == "Russian"

    def test_arabic_text_returns_arabic(self) -> None:
        text = "هذا نص تجريبي باللغة العربية لاختبار كشف اللغة والتعرف عليها. " * 3
        assert detect_language(text) == "Arabic"

    def test_short_text_returns_none(self) -> None:
        assert detect_language("hi") is None

    def test_empty_text_returns_none(self) -> None:
        assert detect_language("") is None

    def test_numbers_only_returns_none(self) -> None:
        assert detect_language("12345 67890 11111 22222 33333 44444") is None
