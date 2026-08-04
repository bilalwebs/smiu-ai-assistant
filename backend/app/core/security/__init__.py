"""Security primitives (Phase 6).

Purpose:
    Cryptographic building blocks used by the authentication service —
    Argon2id password hashing with a password-strength policy, and signed
    JWT utilities for access/verification tokens plus opaque refresh-token
    generation and hashing (API_SPECIFICATION.md §5; BACKEND_ARCHITECTURE.md §9).

Modules:
    - :mod:`password` — Argon2id hashing + policy validation.
    - :mod:`jwt` — token create/decode, refresh-token generation/hashing.
"""
