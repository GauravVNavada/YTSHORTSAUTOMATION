"""
Script deduplication — TF-IDF cosine similarity checking.

Per MASTER_BLUEPRINT §7 Layer 5: Ensure script has <70% similarity
to the last 50 generated scripts to avoid repetition.
"""
import re
import math
from collections import Counter
from typing import Optional

from backend.core.logger import get_logger

logger = get_logger(__name__)


def check_dedup(
    narration: str,
    previous_scripts: list[str],
    threshold: float = 0.70,
) -> Optional[str]:
    """Check if narration is too similar to previous scripts.

    Uses TF-IDF cosine similarity per MASTER_BLUEPRINT §7 Layer 5.

    Args:
        narration: The new script narration text.
        previous_scripts: List of up to 50 previous narrations.
        threshold: Maximum allowed similarity (default 0.70).

    Returns:
        Issue string if too similar, None if unique enough.
    """
    if not previous_scripts:
        return None

    new_tfidf = _compute_tfidf(narration, previous_scripts + [narration])

    for i, prev in enumerate(previous_scripts):
        prev_tfidf = _compute_tfidf(prev, previous_scripts + [narration])
        similarity = _cosine_similarity(new_tfidf, prev_tfidf)

        if similarity >= threshold:
            logger.warning(
                f"Dedup: script too similar ({similarity:.2f}) "
                f"to script #{i + 1}",
            )
            return (
                f"Script is {similarity:.0%} similar to a recent script "
                f"(threshold: {threshold:.0%}). Generate a more unique angle."
            )

    return None


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    return re.findall(r'\b[a-z]+\b', text.lower())


def _compute_tfidf(doc: str, corpus: list[str]) -> dict[str, float]:
    """Compute TF-IDF vector for a document.

    Args:
        doc: The document text.
        corpus: All documents for IDF calculation.

    Returns:
        Dict mapping terms to TF-IDF weights.
    """
    tokens = _tokenize(doc)
    if not tokens:
        return {}

    # TF: term frequency in document
    tf = Counter(tokens)
    max_freq = max(tf.values())

    # IDF: inverse document frequency across corpus
    n_docs = len(corpus)
    doc_freq = Counter()
    for d in corpus:
        seen = set(_tokenize(d))
        for term in seen:
            doc_freq[term] += 1

    # TF-IDF
    tfidf = {}
    for term, freq in tf.items():
        tf_val = freq / max_freq
        idf_val = math.log(n_docs / (1 + doc_freq.get(term, 0)))
        tfidf[term] = tf_val * idf_val

    return tfidf


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Compute cosine similarity between two TF-IDF vectors.

    Args:
        a: First TF-IDF vector.
        b: Second TF-IDF vector.

    Returns:
        Similarity score (0.0 to 1.0).
    """
    if not a or not b:
        return 0.0

    all_terms = set(a.keys()) | set(b.keys())
    dot = sum(a.get(t, 0) * b.get(t, 0) for t in all_terms)
    mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)
