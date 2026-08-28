from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import append_event
from .models import Deployment, Service


async def seed_demo_data(session: AsyncSession) -> None:
    if await session.scalar(select(func.count(Service.id))):
        return
    now = datetime.now(UTC)
    services = [
        Service(
            id=str(uuid4()),
            slug="checkout-api",
            name="Checkout API",
            owner_team="commerce-platform",
            repository="https://github.com/kyan9400/checkout-api",
            created_at=now - timedelta(days=120),
        ),
        Service(
            id=str(uuid4()),
            slug="edge-web",
            name="Edge Web",
            owner_team="experience",
            repository="https://github.com/kyan9400/edge-web",
            created_at=now - timedelta(days=100),
        ),
    ]
    session.add_all(services)
    await session.flush()
    for index in range(24):
        service = services[index % len(services)]
        created = now - timedelta(days=23 - index, hours=(index * 3) % 18)
        failed = index in {5, 14, 19}
        status = "failed" if failed else "succeeded"
        finished = created + timedelta(minutes=12 + index % 9)
        deployment = Deployment(
            id=str(uuid4()),
            service_id=service.id,
            environment="production" if index % 4 else "staging",
            revision=f"{index + 1:07x}-release",
            status=status,
            source="github",
            change_kind="urgent" if index in {5, 19} else "normal",
            started_at=created,
            finished_at=finished,
            recovered_at=finished + timedelta(minutes=25 + index) if failed else None,
            lead_time_seconds=900 + index * 77,
            failure_reason="synthetic checkout regression" if failed else None,
            idempotency_key=f"demo-{index}",
            created_at=created,
        )
        session.add(deployment)
        await session.flush()
        await append_event(
            session,
            action="deployment.created",
            entity_type="deployment",
            entity_id=deployment.id,
            payload={"service": service.slug, "status": status, "revision": deployment.revision},
        )
    await session.commit()
