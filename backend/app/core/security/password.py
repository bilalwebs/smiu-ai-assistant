"""Argon2id password hashing and password-strength policy (API_SPECIFICATION.md §12.5).

Purpose:
    Centralize credential hashing (Argon2id, the preference recorded in the
    Phase 6 plan) and the account password policy. The policy is enforced at
    registration and password change; hashes are verified and transparently
    rehashed when the configured parameters change.

Responsibilities:
    - Hash plaintext passwords with Argon2id (encoded PHC strings).
    - Verify a candidate password against an encoded hash.
    - Report whether a stored hash should be rehashed (parameter drift).
    - Validate passwords against the documented strength policy.

Notes:
    Argon2 is CPU/memory bound by design. Callers in async code must use the
    ``*_async`` wrappers, which run the work in the default thread pool so the
    event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

#: Minimum password length (API_SPECIFICATION.md §12.5).
PASSWORD_MIN_LENGTH = 8

#: Maximum password length to prevent Argon2 DoS via oversized inputs.
PASSWORD_MAX_LENGTH = 128

_PASSWORD_UPPERCASE = re.compile(r"[A-Z]")
_PASSWORD_LOWERCASE = re.compile(r"[a-z]")
_PASSWORD_DIGIT = re.compile(r"[0-9]")
_PASSWORD_SPECIAL = re.compile(r"[^A-Za-z0-9]")

#: Shared hasher with argon2-cffi defaults (Argon2id, 64 MiB memory).
_HASHER = PasswordHasher()


def hash_password(password: str) -> str:
    """Return the Argon2id-encoded hash of ``password``."""
    return _HASHER.hash(password)


async def hash_password_async(password: str) -> str:
    """Hash ``password`` off the event loop (Argon2 is CPU-bound)."""
    return await asyncio.to_thread(hash_password, password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Return ``True`` when ``password`` matches ``encoded_hash``.

    Malformed hashes verify as ``False`` rather than raising, so callers get a
    single, safe failure mode.
    """
    try:
        return _HASHER.verify(encoded_hash, password)
    except (VerificationError, InvalidHashError):
        return False


async def verify_password_async(password: str, encoded_hash: str) -> bool:
    """Verify ``password`` against ``encoded_hash`` off the event loop."""
    return await asyncio.to_thread(verify_password, password, encoded_hash)


def needs_rehash(encoded_hash: str) -> bool:
    """Return ``True`` when the hash should be upgraded to current parameters."""
    try:
        return _HASHER.check_needs_rehash(encoded_hash)
    except InvalidHashError:
        return True


def password_policy_errors(password: str) -> list[str]:
    """Return the policy violations for ``password`` (empty when compliant).

    Rules (API_SPECIFICATION.md §12.5): minimum length 8, at least one
    uppercase letter, one lowercase letter, one digit, and one special
    character.  A maximum length of 128 characters prevents DoS via
    oversized inputs to Argon2.
    """
    errors: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        errors.append(f"must be at most {PASSWORD_MAX_LENGTH} characters")
    if not _PASSWORD_UPPERCASE.search(password):
        errors.append("must contain at least one uppercase letter")
    if not _PASSWORD_LOWERCASE.search(password):
        errors.append("must contain at least one lowercase letter")
    if not _PASSWORD_DIGIT.search(password):
        errors.append("must contain at least one number")
    if not _PASSWORD_SPECIAL.search(password):
        errors.append("must contain at least one special character")
    return errors
