"""Local latent-semantic retrieval for creator and advertising category text."""

from functools import lru_cache

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize


@lru_cache(maxsize=4)
def _fit_corpus(documents: tuple[str, ...]):
    vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=12000,
    )
    document_vectors = vectorizer.fit_transform(documents)
    n_components = min(64, document_vectors.shape[0] - 1, document_vectors.shape[1] - 1)
    if n_components >= 2:
        latent_model = TruncatedSVD(n_components=n_components, n_iter=7, random_state=42)
        projected_documents = normalize(latent_model.fit_transform(document_vectors))
    else:
        latent_model = None
        projected_documents = document_vectors
    return vectorizer, latent_model, projected_documents


def semantic_scores(query: str, documents: list[str]) -> list[float]:
    """Return LSA cosine similarities for a query against a stable document corpus."""
    if not documents:
        return []
    cleaned_documents = tuple(" ".join(document.split()) or "creator profile" for document in documents)
    vectorizer, latent_model, document_vectors = _fit_corpus(cleaned_documents)
    query_vector = vectorizer.transform([query])
    if latent_model is not None:
        query_vector = normalize(latent_model.transform(query_vector))
    scores = cosine_similarity(query_vector, document_vectors).ravel()
    return [float(score) for score in np.nan_to_num(scores, nan=0.0)]


def keyword_overlap(query: str, document: str, limit: int = 5) -> list[str]:
    query_words = {word.casefold() for word in query.split() if len(word) > 2}
    doc_words = {word.casefold().strip(".,!?;:#@()[]") for word in document.split() if len(word) > 2}
    return sorted(query_words & doc_words)[:limit]
