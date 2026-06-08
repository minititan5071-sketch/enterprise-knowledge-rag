from pathlib import Path

from backend.app.rag.chunking import TextPage


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


def extract_text_pages(path: Path) -> list[TextPage]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported document type: {suffix}")

    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    return [TextPage(page_number=None, text=path.read_text(encoding="utf-8", errors="ignore"))]


def _extract_pdf(path: Path) -> list[TextPage]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[TextPage] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(TextPage(page_number=index, text=page.extract_text() or ""))
    return pages


def _extract_docx(path: Path) -> list[TextPage]:
    from docx import Document as DocxDocument

    document = DocxDocument(str(path))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return [TextPage(page_number=None, text=text)]

