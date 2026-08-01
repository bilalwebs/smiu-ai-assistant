"""Middleware package.

Purpose:
    Own the HTTP middleware defined by BACKEND_ARCHITECTURE.md §17:
    request id/correlation, request logging + timing, security headers, and CORS.

Responsibilities:
    - Register middleware in the documented order (CORS/security outermost,
      logging wrapping request handling).
    - Keep each middleware small, stateless, and configuration-driven.

Usage:
    The application factory adds these; no router code should import them
    directly.
"""
