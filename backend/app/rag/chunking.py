from datetime import datetime
from typing import NamedTuple

from backend.app.core.config import settings


class TextPage(NamedTuple):
    page_number: int | None
    text: str


class Chunk(NamedTuple):
    text: str
    metadata: dict


def chunk_pages(
    pages: list[TextPage],
    document_id: str,
    workspace_id: str,
    filename: str,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0
    created_at = datetime.utcnow().isoformat() + "Z"
    chunk_size = settings.chunk_size_chars
    overlap = settings.chunk_overlap_chars

    for page in pages:
        text = " ".join(page.text.split())
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        metadata={
                            "document_id": document_id,
                            "workspace_id": workspace_id,
                            "filename": filename,
                            "page_number": page.page_number,
                            "chunk_index": chunk_index,
                            "created_at": created_at,
                        },
                    )
                )
                chunk_index += 1
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks

