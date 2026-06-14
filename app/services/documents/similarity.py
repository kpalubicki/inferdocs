"""Keyword-based TF-IDF cosine similarity between documents."""

from __future__ import annotations

import math
import re
from collections import Counter

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "that", "this", "these", "those",
    "it", "its", "i", "we", "you", "he", "she", "they", "as", "if", "not",
    "no", "so", "than", "then", "up", "out", "about", "into", "more",
    "all", "also", "can", "our", "your", "their", "which", "what", "how",
    "his", "her", "its", "we", "they", "them", "my", "me", "us",
}


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOP_WORDS]


def _tf(tokens: list[str]) -> dict[str, float]:
    total = len(tokens)
    if total == 0:
        return {}
    counts = Counter(tokens)
    return {word: count / total for word, count in counts.items()}


def _idf(corpus: list[list[str]]) -> dict[str, float]:
    n = len(corpus)
    doc_freq: dict[str, int] = {}
    for tokens in corpus:
        for word in set(tokens):
            doc_freq[word] = doc_freq.get(word, 0) + 1
    return {word: math.log((n + 1) / (freq + 1)) + 1 for word, freq in doc_freq.items()}


def _tfidf_vector(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    return {word: tf[word] * idf.get(word, 1.0) for word in tf}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def find_similar(
    target_text: str,
    candidates: list[tuple[str, str]],  # [(doc_id, text), ...]
    top_n: int = 5,
) -> list[tuple[str, float]]:
    """Return up to top_n (doc_id, score) tuples, sorted by similarity descending.

    Score is cosine similarity on TF-IDF vectors.
    """
    if not candidates:
        return []

    all_texts = [target_text] + [text for _, text in candidates]
    all_tokens = [_tokenize(t) for t in all_texts]
    idf = _idf(all_tokens)

    target_vec = _tfidf_vector(_tf(all_tokens[0]), idf)

    results: list[tuple[str, float]] = []
    for i, (doc_id, _) in enumerate(candidates):
        candidate_vec = _tfidf_vector(_tf(all_tokens[i + 1]), idf)
        score = _cosine(target_vec, candidate_vec)
        results.append((doc_id, round(score, 4)))

    results.sort(key=lambda x: -x[1])
    return results[:top_n]
