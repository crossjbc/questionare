
# Isolated in its own module (not utils.py) because this makes a network
# call - fundamentally different from the pure text functions. Anything
# that touches an external API deserves its own file so it's obvious
# what needs mocking in tests and what can fail due to network issues.

import time

from django.conf import settings
from google import genai
from google.genai.types import EmbedContentConfig

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768  # must match ReferenceSnippet.embedding's VectorField(dimensions=768)

_client = None


def _get_client():
    # Lazy singleton: don't create the client at import time (e.g. during
    # migrations, when the API key may not even be configured yet).
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


class EmbeddingError(Exception):
    """Raised when embedding a piece of text fails after retries."""


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 3) -> list[float]:
    """
    Get an embedding vector for a single piece of text.

    task_type: "RETRIEVAL_DOCUMENT" for stored reference chunks (this is
    what process_document uses), "RETRIEVAL_QUERY" for a search query at
    retrieval time (Step 8) - same model, different hint, better accuracy
    for each role.
    """
    client = _get_client()
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_DIMENSIONS,
                ),
            )
            return response.embeddings[0].values

        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # 2s, 4s, 8s backoff

    raise EmbeddingError(f"Failed to embed text after {max_retries} attempts: {last_error}")