import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditEvent


def _canonical_payload(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _event_hash(
    previous_hash: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
    occurred_at: datetime,
) -> str:
    value = "|".join(
        [
            previous_hash,
            action,
            entity_type,
            entity_id,
            _canonical_payload(payload),
            occurred_at.isoformat(),
        ]
    )
    return hashlib.sha256(value.encode()).hexdigest()


async def append_event(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> AuditEvent:
    previous = await session.scalar(
        select(AuditEvent).order_by(AuditEvent.sequence.desc()).limit(1)
    )
    previous_hash = previous.event_hash if previous else "0" * 64
    occurred_at = datetime.now(UTC)
    event = AuditEvent(
        id=str(uuid4()),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        previous_hash=previous_hash,
        event_hash=_event_hash(previous_hash, action, entity_type, entity_id, payload, occurred_at),
        occurred_at=occurred_at,
    )
    session.add(event)
    await session.flush()
    return event
