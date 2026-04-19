"""Lightweight script-based language detection."""

import unicodedata


def detect_language(text: str) -> str | None:
    """Detect the primary language/script of the text.

    Uses Unicode block analysis to identify the dominant script.
    Returns a human-readable language name suitable for LLM prompts,
    or None if the text is too short or indeterminate.
    """
    if not text or len(text.strip()) < 20:
        return None

    sample = text[:2000]
    counts: dict[str, int] = {}

    for ch in sample:
        if ch.isspace() or ch.isdigit() or not ch.isalpha():
            continue
        cp = ord(ch)
        script = _script_of(cp)
        if script:
            counts[script] = counts.get(script, 0) + 1

    if not counts:
        return None

    total = sum(counts.values())
    dominant, top_count = max(counts.items(), key=lambda x: x[1])

    if top_count / total < 0.4:
        return None

    return _SCRIPT_TO_LANGUAGE.get(dominant)


def _script_of(cp: int) -> str | None:
    if 0x0041 <= cp <= 0x007A or 0x00C0 <= cp <= 0x024F:
        return "latin"
    if 0x0400 <= cp <= 0x04FF:
        return "cyrillic"
    if 0x0600 <= cp <= 0x06FF:
        return "arabic"
    if 0x0900 <= cp <= 0x097F:
        return "devanagari"
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
        return "cjk"
    if 0x3040 <= cp <= 0x30FF:
        return "japanese"
    if 0xAC00 <= cp <= 0xD7AF:
        return "korean"
    if 0x0370 <= cp <= 0x03FF:
        return "greek"
    if 0x0590 <= cp <= 0x05FF:
        return "hebrew"
    if 0x0E00 <= cp <= 0x0E7F:
        return "thai"
    return None


_SCRIPT_TO_LANGUAGE: dict[str, str] = {
    "latin": "English",
    "cyrillic": "Russian",
    "arabic": "Arabic",
    "devanagari": "Hindi",
    "cjk": "Chinese",
    "japanese": "Japanese",
    "korean": "Korean",
    "greek": "Greek",
    "hebrew": "Hebrew",
    "thai": "Thai",
}
