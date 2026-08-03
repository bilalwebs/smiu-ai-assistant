"""``departments`` repository helpers (DATABASE_DESIGN.md §14)."""

from __future__ import annotations

from app.repositories import DepartmentRepository


async def test_get_by_code_hit(db_session, department_factory) -> None:
    dept = await department_factory(code="CSE")
    repo = DepartmentRepository(db_session)
    fetched = await repo.get_by_code("CSE")
    assert fetched is not None
    assert fetched.id == dept.id


async def test_get_by_code_miss(db_session, department_factory) -> None:
    await department_factory()
    repo = DepartmentRepository(db_session)
    assert await repo.get_by_code("NOPE") is None


async def test_get_by_code_excludes_soft_deleted(db_session, department_factory) -> None:
    dept = await department_factory(code="MATH")
    repo = DepartmentRepository(db_session)
    await repo.soft_delete(dept)
    assert await repo.get_by_code("MATH") is None


async def test_list_active_filters_and_sorts(db_session, department_factory) -> None:
    dept_a = await department_factory(name="Beta", sort_order=2)
    dept_b = await department_factory(name="Alpha", sort_order=1)
    await department_factory(name="Zulu", sort_order=0, is_active=False)
    repo = DepartmentRepository(db_session)
    rows = await repo.list_active()
    assert [row.id for row in rows] == [dept_b.id, dept_a.id]


async def test_list_active_ties_break_by_name(db_session, department_factory) -> None:
    first = await department_factory(name="Admissions", sort_order=0)
    second = await department_factory(name="Exams", sort_order=0)
    repo = DepartmentRepository(db_session)
    rows = await repo.list_active()
    assert [row.id for row in rows] == [first.id, second.id]
