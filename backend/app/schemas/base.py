"""Shared Pydantic building blocks for the API read schemas.

Purpose:
    Standardize how ORM entities are exposed to clients: attribute-based
    population and a single UTC ISO-8601 ``Z`` datetime serialization that
    matches the response contract (API_SPECIFICATION.md §7).

Responsibilities:
    - ``ApiModel`` — base class that populates from ORM attributes.
    - ``UtcDateTime`` — datetime type serialized as UTC ISO-8601 with a
      trailing ``Z`` (naive DB timestamps are interpreted as UTC).

Usage:
    Domain read schemas subclass :class:`ApiModel` and use ``model_validate``
    against ORM instances.
"""

from __future__ import annotations

from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer


def to_utc_iso(value: datetime) -> str:
    """Serialize a datetime as UTC ISO-8601 with a trailing ``Z``.

    SQLite stores ``CURRENT_TIMESTAMP`` values as naive UTC datetimes, so a
    naive value is treated as UTC rather than converted from local time.
    """
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value.isoformat().replace("+00:00", "Z")


def _ip_to_str(value: object) -> object:
    """Normalize an ORM IP value to its textual form.

    The ``inet`` column type returns ``IPv4Address``/``IPv6Address`` objects
    on PostgreSQL (asyncpg) while SQLite's varchar variant returns plain
    strings; this keeps the API contract a stable ``string`` on both.
    """
    if isinstance(value, (IPv4Address, IPv6Address)):
        return str(value)
    return value


IPAddressStr = Annotated[str, BeforeValidator(_ip_to_str)]


UtcDateTime = Annotated[datetime, PlainSerializer(to_utc_iso, return_type=str)]


class ApiModel(BaseModel):
    """Base read model: populated from ORM attributes (API_SPECIFICATION.md §7)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
