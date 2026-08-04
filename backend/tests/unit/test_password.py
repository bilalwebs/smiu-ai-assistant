"""Password-hashing and policy unit tests (API_SPECIFICATION.md §12.5)."""

from __future__ import annotations

import pytest

from app.core.security.password import (
    PASSWORD_MIN_LENGTH,
    hash_password,
    hash_password_async,
    needs_rehash,
    password_policy_errors,
    verify_password,
    verify_password_async,
)

GOOD_PASSWORD = "Sup3r!secure"


def test_hash_round_trip() -> None:
    """A freshly hashed password verifies with its own hash."""
    hashed = hash_password(GOOD_PASSWORD)
    assert verify_password(GOOD_PASSWORD, hashed) is True


def test_hash_is_salted_and_unique() -> None:
    """Two hashes of the same password differ (Argon2 salts each hash)."""
    assert hash_password(GOOD_PASSWORD) != hash_password(GOOD_PASSWORD)


def test_verify_rejects_wrong_password() -> None:
    hashed = hash_password(GOOD_PASSWORD)
    assert verify_password("Wrong!password", hashed) is False


def test_verify_rejects_malformed_hash() -> None:
    """A corrupt hash string fails closed instead of raising."""
    assert verify_password(GOOD_PASSWORD, "not-an-argon2-hash") is False


def test_fresh_hash_does_not_need_rehash() -> None:
    assert needs_rehash(hash_password(GOOD_PASSWORD)) is False


async def test_async_wrappers_round_trip() -> None:
    hashed = await hash_password_async(GOOD_PASSWORD)
    assert await verify_password_async(GOOD_PASSWORD, hashed) is True
    assert await verify_password_async("nope", hashed) is False


def test_compliant_password_passes_policy() -> None:
    assert password_policy_errors(GOOD_PASSWORD) == []


@pytest.mark.parametrize(
    ("password", "violated_rule"),
    [
        ("Short1!", "at least 8 characters"),
        ("uppercase1!", "at least one uppercase letter"),
        ("UPPERCASE1!", "at least one lowercase letter"),
        ("NoDigits!xx", "at least one number"),
        ("NoSpecial1x", "at least one special character"),
    ],
)
def test_password_policy_reports_each_violation(
    password: str, violated_rule: str
) -> None:
    errors = password_policy_errors(password)
    assert any(violated_rule in error for error in errors)


def test_password_policy_min_length_constant() -> None:
    assert PASSWORD_MIN_LENGTH == 8
