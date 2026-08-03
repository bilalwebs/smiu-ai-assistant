"""Model mixin tests (DATABASE_DESIGN.md §4.4, §7, §26, §34.5).

Exercises the reusable column mixins and the combined ``BaseModel`` against a
real in-memory SQLite schema so column defaults and lifecycle helpers are
verified through the dialect, not just the ORM metadata.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import BaseModel
from app.models.mixins import AuditMixin, CreatedAtMixin, UUIDPrimaryKeyMixin


class SampleRecord(BaseModel, Base):
    __tablename__ = "unit_test_sample_records"

    name: Mapped[str] = mapped_column(String(120), nullable=False)


class AuditRecord(AuditMixin, BaseModel, Base):
    __tablename__ = "unit_test_audit_records"

    title: Mapped[str] = mapped_column(String(120), nullable=False)


class AppendOnlyRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "unit_test_append_only_records"


def test_uuid_primary_key_column() -> None:
    column = SampleRecord.__table__.columns["id"]
    assert column.primary_key is True
    assert column.nullable is False


def test_base_model_standard_column_set() -> None:
    columns = set(SampleRecord.__table__.columns.keys())
    assert {"id", "created_at", "updated_at", "deleted_at", "version"} <= columns


def test_append_only_column_set() -> None:
    columns = set(AppendOnlyRecord.__table__.columns.keys())
    assert columns == {"id", "created_at"}


def test_updated_at_has_onupdate() -> None:
    assert SampleRecord.__table__.columns["updated_at"].onupdate is not None


async def test_timestamps_populated_on_insert(db_session: AsyncSession) -> None:
    record = SampleRecord(name="smiu")
    db_session.add(record)
    await db_session.commit()
    assert record.created_at is not None
    assert record.updated_at is not None


async def test_soft_delete_lifecycle(db_session: AsyncSession) -> None:
    record = SampleRecord(name="smiu")
    db_session.add(record)
    await db_session.commit()
    assert record.is_deleted is False

    record.soft_delete()
    assert record.is_deleted is True
    assert record.deleted_at is not None

    record.soft_delete()
    assert record.deleted_at is not None

    record.restore()
    assert record.is_deleted is False
    assert record.deleted_at is None


async def test_version_default_and_increment(db_session: AsyncSession) -> None:
    record = SampleRecord(name="smiu")
    db_session.add(record)
    await db_session.commit()
    assert record.version == 1

    record.increment_version()
    await db_session.commit()
    assert record.version == 2


def test_audit_mixin_actor_columns() -> None:
    columns = AuditRecord.__table__.columns
    assert "created_by" in columns
    assert "updated_by" in columns
    assert columns["created_by"].nullable is True
    assert columns["updated_by"].nullable is True
