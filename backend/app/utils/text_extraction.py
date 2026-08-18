"""PDF text extraction utility.

Purpose:
    Extract readable text from uploaded PDF files using ``pypdf``. Used
    during document upload to populate the ``extracted_text_path`` column
    so the AI workflow can use user-uploaded document context.

Safety:
    - Returns empty string on extraction failure rather than raising.
    - Never exposes raw exception details to the caller.
"""

from __future__ import annotations

import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)

#: Maximum pages to extract from a single PDF to prevent excessive memory use.
_MAX_PAGES = 200


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes.

    Returns the concatenated text of all pages, or an empty string if
    extraction fails or produces no readable text.
    """
    try:
        import io

        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:_MAX_PAGES]
        text_parts: list[str] = []
        for page in pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception:
        logger.exception("Failed to extract text from PDF")
        return ""
