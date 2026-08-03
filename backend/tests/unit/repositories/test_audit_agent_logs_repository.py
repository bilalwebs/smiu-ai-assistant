"""``audit_logs`` and ``agent_logs`` repository helpers (DATABASE_DESIGN.md §24)."""

from __future__ import annotations

from datetime import timedelta

from app.repositories import AgentLogRepository, AuditLogRepository
from app.utils.time import utc_now


async def test_audit_list_by_actor_newest_first(
    db_session, audit_log_factory, user_factory
) -> None:
    actor = await user_factory()
    other = await user_factory()
    now = utc_now()
    await audit_log_factory(actor_user_id=actor.id, action="one", created_at=now)
    await audit_log_factory(
        actor_user_id=actor.id, action="two", created_at=now - timedelta(minutes=1)
    )
    await audit_log_factory(actor_user_id=other.id)
    repo = AuditLogRepository(db_session)
    rows = await repo.list_by_actor(actor.id)
    assert [row.action for row in rows] == ["one", "two"]


async def test_audit_list_by_resource(db_session, audit_log_factory) -> None:
    now = utc_now()
    r1 = await audit_log_factory(
        resource_type="request", resource_id="req-1", created_at=now
    )
    r2 = await audit_log_factory(
        resource_type="request",
        resource_id="req-1",
        created_at=now - timedelta(minutes=1),
    )
    await audit_log_factory(resource_type="request", resource_id="req-2")
    await audit_log_factory(resource_type="user")
    repo = AuditLogRepository(db_session)
    rows = await repo.list_by_resource("request", "req-1")
    assert [row.id for row in rows] == [r1.id, r2.id]
    all_requests = await repo.list_by_resource("request")
    assert len(all_requests) == 3


async def test_agent_list_by_conversation_newest_first(
    db_session, agent_log_factory, user_factory, conversation_factory
) -> None:
    conv = await conversation_factory(user_id=(await user_factory()).id)
    other_conv = await conversation_factory(user_id=(await user_factory()).id)
    now = utc_now()
    await agent_log_factory(conversation_id=conv.id, intent="one", created_at=now)
    await agent_log_factory(
        conversation_id=conv.id, intent="two", created_at=now - timedelta(minutes=1)
    )
    await agent_log_factory(conversation_id=other_conv.id)
    repo = AgentLogRepository(db_session)
    rows = await repo.list_by_conversation(conv.id)
    assert [row.intent for row in rows] == ["one", "two"]
