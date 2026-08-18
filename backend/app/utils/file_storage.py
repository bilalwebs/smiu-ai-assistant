"""File storage utility for uploaded documents.

Purpose:
    Provide safe filesystem operations for user-uploaded files: writing bytes
    to a configurable storage directory with unique filenames, and computing
    SHA-256 checksums. Original filenames are never used for filesystem paths.

Safety:
    - Storage path is configurable (``STORAGE_PATH`` setting).
    - Stored filenames are UUID-based, preventing path traversal.
    - The caller must validate file type and size before calling ``save_file``.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from app.config.settings import get_settings


def get_storage_root() -> Path:
    """Return the resolved storage root directory, creating it if needed."""
    settings = get_settings()
    root = Path(settings.storage_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def generate_stored_filename(original_filename: str) -> str:
    """Generate a safe unique stored filename from the original.

    Uses a UUID4 to prevent path traversal and filename collisions. The
    original extension is preserved for content-type identification.
    """
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def compute_checksum(data: bytes) -> str:
    """Return the SHA-256 hex digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


async def save_file(data: bytes, stored_filename: str) -> Path:
    """Write ``data`` to the storage root under ``stored_filename``.

    Returns the resolved file path. Creates subdirectories as needed.
    """
    root = get_storage_root()
    file_path = root / stored_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(data)
    return file_path


def get_extracted_text_path(stored_filename: str) -> Path:
    """Return the path where extracted text for a document is stored.

    Extracted text is stored alongside the original file with a ``.txt``
    extension appended to the stored filename.
    """
    root = get_storage_root()
    return root / f"{stored_filename}.txt"


async def save_extracted_text(stored_filename: str, text: str) -> Path:
    """Save extracted text alongside the stored file.

    Returns the resolved path of the text file.
    """
    text_path = get_extracted_text_path(stored_filename)
    text_path.write_text(text, encoding="utf-8")
    return text_path


def read_extracted_text(extracted_text_path: str) -> str | None:
    """Read extracted text from the given path.

    Returns the text content, or ``None`` if the file does not exist.
    """
    path = Path(extracted_text_path)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
