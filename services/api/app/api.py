import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import append_event
from .auth import require_api_key, verify_webhook_signature
from .db import get_session
from .metrics import build_dora_response
from .models import AuditEvent, Deployment, Service
from .schemas import (
    DeploymentCreate,
    DeploymentPatch,
    DeploymentRead,
    DORAResponse,
    ServiceCreate,
    ServiceRead,
)

router = APIRouter(prefix="/api/v1")


def deployment_response(deployment: Deployment, service: Service) -> DeploymentRead:
    return DeploymentRead(
        id=deployment.id,
        service_slug=service.slug,
        environment=deployment.environment,
        revision=deployment.revision,
        status=deployment.status,
        source=deployment.source,
        change_kind=deployment.change_kind,
        started_at=deployment.started_at,
        finished_at=deployment.finished_at,
        recovered_at=deployment.recovered_at,
        lead_time_seconds=deployment.lead_time_seconds,
        failure_reason=deployment.failure_reason,
        created_at=deployment.created_at,
    )


@router.get("/services", response_model=list[ServiceRead], tags=["services"])
async def list_services(session: AsyncSession = Depends(get_session)) -> list[Service]:
    return list((await session.scalars(select(Service).order_by(Service.name.asc()))).all())


@router.post(
    "/services",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
    tags=["services"],
)
async def create_service(
    payload: ServiceCreate, session: AsyncSession = Depends(get_session)
) -> Service:
    service = Service(
        id=str(uuid4()),
        slug=payload.slug,
        name=payload.name,
        owner_team=payload.owner_team,
        repository=str(payload.repository),
        created_at=datetime.now(UTC),
    )
    session.add(service)
    try:
        await session.flush()
        await append_event(
            session,
            action="service.created",
            entity_type="service",
            entity_id=service.id,
            payload={"slug": service.slug, "owner_team": service.owner_team},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="service slug already exists",
        ) from exc
    return service


@router.get("/deployments", response_model=list[DeploymentRead], tags=["deployments"])
async def list_deployments(
    service_slug: str | None = None,
    environment: str | None = Query(default=None, pattern="^(production|staging|preview)$"),
    deployment_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(running|succeeded|failed|rolled_back)$",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[DeploymentRead]:
    statement = select(Deployment, Service).join(Service)
    if service_slug:
        statement = statement.where(Service.slug == service_slug)
    if environment:
        statement = statement.where(Deployment.environment == environment)
    if deployment_status:
        statement = statement.where(Deployment.status == deployment_status)
    rows = (
        await session.execute(statement.order_by(Deployment.created_at.desc()).limit(limit))
    ).all()
    return [deployment_response(deployment, service) for deployment, service in rows]


@router.post(
    "/deployments",
    response_model=DeploymentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
    tags=["deployments"],
)
async def create_deployment(
    payload: DeploymentCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> DeploymentRead:
    service = await session.scalar(select(Service).where(Service.slug == payload.service_slug))
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found")
    if idempotency_key:
        if len(idempotency_key) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key is too long",
            )
        existing = await session.scalar(
            select(Deployment).where(
                Deployment.service_id == service.id, Deployment.idempotency_key == idempotency_key
            )
        )
        if existing:
            return deployment_response(existing, service)
    now = datetime.now(UTC)
    started_at = payload.started_at or now
    finished_at = payload.finished_at or (now if payload.status != "running" else None)
    deployment = Deployment(
        id=str(uuid4()),
        service_id=service.id,
        environment=payload.environment,
        revision=payload.revision,
        status=payload.status,
        source=payload.source,
        change_kind=payload.change_kind,
        started_at=started_at,
        finished_at=finished_at,
        recovered_at=payload.recovered_at,
        lead_time_seconds=payload.lead_time_seconds,
        failure_reason=payload.failure_reason,
        idempotency_key=idempotency_key,
        created_at=now,
    )
    session.add(deployment)
    try:
        await session.flush()
        await append_event(
            session,
            action="deployment.created",
            entity_type="deployment",
            entity_id=deployment.id,
            payload={
                "service": service.slug,
                "environment": deployment.environment,
                "revision": deployment.revision,
                "status": deployment.status,
            },
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if idempotency_key:
            existing = await session.scalar(
                select(Deployment).where(
                    Deployment.service_id == service.id,
                    Deployment.idempotency_key == idempotency_key,
                )
            )
            if existing:
                return deployment_response(existing, service)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="deployment conflicts with existing data",
        ) from exc
    return deployment_response(deployment, service)


@router.patch(
    "/deployments/{deployment_id}",
    response_model=DeploymentRead,
    dependencies=[Depends(require_api_key)],
    tags=["deployments"],
)
async def update_deployment(
    deployment_id: str,
    payload: DeploymentPatch,
    session: AsyncSession = Depends(get_session),
) -> DeploymentRead:
    row = (
        await session.execute(
            select(Deployment, Service).join(Service).where(Deployment.id == deployment_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="deployment not found")
    deployment, service = row
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(deployment, field, value)
    if payload.status and payload.status != "running" and deployment.finished_at is None:
        deployment.finished_at = datetime.now(UTC)
    await append_event(
        session,
        action="deployment.updated",
        entity_type="deployment",
        entity_id=deployment.id,
        payload={"changes": {key: str(value) for key, value in changes.items()}},
    )
    await session.commit()
    return deployment_response(deployment, service)


@router.get("/metrics/dora", response_model=DORAResponse, tags=["metrics"])
async def dora_metrics(
    service_slug: str | None = None,
    window_days: int = Query(default=30, ge=7, le=90),
    session: AsyncSession = Depends(get_session),
) -> DORAResponse:
    if service_slug and not await session.scalar(
        select(Service).where(Service.slug == service_slug)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found")
    return await build_dora_response(session, service_slug=service_slug, window_days=window_days)


@router.get("/audit", tags=["audit"])
async def audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    events = list(
        (
            await session.scalars(
                select(AuditEvent).order_by(AuditEvent.sequence.desc()).limit(limit)
            )
        ).all()
    )
    return [
        {
            "sequence": event.sequence,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "payload": event.payload,
            "previous_hash": event.previous_hash,
            "event_hash": event.event_hash,
            "occurred_at": event.occurred_at,
        }
        for event in events
    ]


@router.post("/webhooks/github", status_code=status.HTTP_202_ACCEPTED, tags=["webhooks"])
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid content-length",
            ) from exc
        if declared_length > 1_048_576:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="payload too large",
            )
    body = await request.body()
    if len(body) > 1_048_576 or not verify_webhook_signature(body, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid webhook signature",
        )
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid JSON payload",
        ) from exc
    if x_github_event not in {"deployment_status", "deployment"}:
        return {"status": "ignored", "reason": "event is not a deployment"}
    repository_data = payload.get("repository") or {}
    repository = repository_data.get("name") or repository_data.get("full_name", "").split("/")[-1]
    service = await session.scalar(select(Service).where(Service.slug == repository))
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not registered")
    deployment_data = payload.get("deployment_status") or payload.get("deployment") or {}
    state = deployment_data.get("state", deployment_data.get("status", "running"))
    state = {
        "success": "succeeded",
        "failure": "failed",
        "error": "failed",
        "inactive": "rolled_back",
    }.get(state, state)
    if state not in {"running", "succeeded", "failed", "rolled_back"}:
        return {"status": "ignored", "reason": "unsupported deployment state"}
    revision = deployment_data.get("sha") or deployment_data.get("ref") or "github-event"
    key = x_github_delivery or str(uuid4())
    request_payload = DeploymentCreate(
        service_slug=service.slug,
        environment=deployment_data.get("environment", "production"),
        revision=revision,
        status=state,
        source="github",
    )
    result = await create_deployment(request_payload, key, session)
    return {"status": "recorded", "deployment_id": result.id}
