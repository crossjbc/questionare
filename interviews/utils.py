# app_name/utils/chunking.py
#
# Pure text-processing utility: no DB access, no external API calls.
# This makes it easy to unit test in isolation - just call it with a
# string and check the list of chunks it returns.

from typing import List
import os
from pypdf import PdfReader
from .models import Document, ReferenceSnippet
from .embedding import embed_text, EmbeddingError

def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[str]:
    """
    Split `text` into overlapping chunks, sized by word count.

    chunk_size: target number of words per chunk.
    overlap:    number of words repeated at the start of the next chunk,
                so context isn't lost at chunk boundaries.

    Example: chunk_size=500, overlap=50 means each chunk after the first
    starts 450 words after the previous chunk started - not a full
    500-word jump - so idea continuity survives across the cut.
    """
    if not text or not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    start = 0

    while start < len(words):
        window = words[start : start + chunk_size]
        chunk = " ".join(window).strip()

        # Skip near-empty or trivially short chunks (e.g. a stray page
        # break that split off just a few words) - not useful to embed.
        if len(chunk) > 20:
            chunks.append(chunk)

        start += step

    return chunks




class ExtractionError(Exception):
    """Raised when text can't be extracted from a document's file."""


def extract_text(document) -> str:
    """
    Extract raw text from a Document's uploaded file.

    Supports .txt/.md (read directly) and .pdf (via pypdf).
    Raises ExtractionError with a clear message on failure - this message
    is what gets saved into Document.error_message by the calling task.
    """
    filename = document.file.name
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext in (".txt", ".md"):
            with document.file.open("r") as f:
                return f.read()

        elif ext == ".pdf":
            with document.file.open("rb") as f:
                reader = PdfReader(f)
                pages_text = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
                text = "\n".join(pages_text)

            if not text.strip():
                raise ExtractionError(
                    "No extractable text found in PDF. It may be a scanned "
                    "image PDF, which requires OCR (not supported yet)."
                )
            return text

        else:
            raise ExtractionError(f"Unsupported file type: '{ext}'. Supported: .txt, .md, .pdf")

    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"Failed to extract text from '{filename}': {e}")


# This is the orchestration layer: it calls the two pure functions we
# already built, and is the ONLY piece here that touches the database.
# Keeping extract_text/chunk_text pure and putting all I/O here is what
# makes this function the natural place to plug in Celery later - the
# Celery task in Step 7 will just be a thin wrapper calling this.

def process_document(document: Document) -> None:
    document.status = Document.Status.PROCESSING
    document.error_message = ""
    document.save(update_fields=["status", "error_message"])

    try:
        raw_text = extract_text(document)
        chunks = chunk_text(raw_text)

        if not chunks:
            raise ExtractionError(
                "No usable text chunks were produced. The file may be empty "
                "or contain only whitespace."
            )

        ReferenceSnippet.objects.filter(document=document).delete()

        snippet_objects = [
            ReferenceSnippet(
                track=document.track,
                document=document,
                content=chunk,
                source=document.original_filename or document.file.name,
            )
            for chunk in chunks
        ]
        ReferenceSnippet.objects.bulk_create(snippet_objects)

        # --- NEW: embed each snippet, then save the embeddings ---
        # bulk_create doesn't reliably return usable PKs on every DB
        # backend, so we re-fetch the snippets we just created for this
        # document to get real objects with IDs we can update.
        created_snippets = list(ReferenceSnippet.objects.filter(document=document))

        for snippet in created_snippets:
            try:
                snippet.embedding = embed_text(snippet.content, task_type="RETRIEVAL_DOCUMENT")
            except EmbeddingError as e:
                # Don't let one bad chunk fail the whole document - log
                # and leave that snippet's embedding null, still searchable
                # once retried later.
                snippet.embedding = None
                document.error_message += f"\nEmbedding failed for a chunk: {e}"

        ReferenceSnippet.objects.bulk_update(created_snippets, ["embedding"])
        # --- end new section ---

        document.status = Document.Status.DONE
        document.chunk_count = len(snippet_objects)
        document.save(update_fields=["status", "chunk_count", "error_message"])

    except ExtractionError as e:
        document.status = Document.Status.FAILED
        document.error_message = str(e)
        document.save(update_fields=["status", "error_message"])

    except Exception as e:
        document.status = Document.Status.FAILED
        document.error_message = f"Unexpected error during processing: {e}"
        document.save(update_fields=["status", "error_message"])