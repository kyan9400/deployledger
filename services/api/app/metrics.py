from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import mean

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Deployment, Service
from .schemas import DORAResponse, DORASummary, DORATrendPoint


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile))
    return ordered[index]


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def load_deployments(
    session: AsyncSession, *, service_slug: str | None, since: datetime
) -> list[tuple[Deployment, str]]:
    statement: Select[tuple[Deployment, Service]] = (
        select(Deployment, Service).join(Service).where(Deployment.created_at >= since)
    )
    if service_slug:
        statement = statement.where(Service.slug == service_slug)
    rows = (await session.execute(statement.order_by(Deployment.created_at.asc()))).all()
    return [(deployment, service.slug) for deployment, service in rows]


async def build_dora_response(
    session: AsyncSession, *, service_slug: str | None, window_days: int
) -> DORAResponse:
    now = datetime.now(UTC)
    since = now - timedelta(days=window_days)
    rows = await load_deployments(session, service_slug=service_slug, since=since)
    completed = [
        deployment
        for deployment, _ in rows
        if deployment.status in {"succeeded", "failed", "rolled_back"}
    ]
    succeeded = [deployment for deployment in completed if deployment.status == "succeeded"]
    failed = [
        deployment for deployment in completed if deployment.status in {"failed", "rolled_back"}
    ]
    lead_times = [
        deployment.lead_time_seconds
        for deployment in succeeded
        if deployment.lead_time_seconds is not None
    ]
    recovery_times = [
        int((deployment.recovered_at - deployment.finished_at).total_seconds())
        for deployment in failed
        if deployment.finished_at and deployment.recovered_at
    ]
    denominator = len(completed)
    summary = DORASummary(
        deployment_frequency_per_week=round(len(succeeded) / max(window_days / 7, 1), 2),
        change_lead_time_p50_seconds=_percentile(lead_times, 0.50),
        change_lead_time_p95_seconds=_percentile(lead_times, 0.95),
        change_fail_rate_percent=round((len(failed) / denominator) * 100, 2) if denominator else 0,
        failed_deployment_recovery_p50_seconds=_percentile(recovery_times, 0.50),
        deployment_rework_rate_percent=round(
            (sum(deployment.change_kind == "urgent" for deployment in completed) / denominator)
            * 100,
            2,
        )
        if denominator
        else 0,
    )

    buckets: dict[str, list[Deployment]] = defaultdict(list)
    for deployment, _ in rows:
        day = _as_utc(deployment.created_at).date().isoformat()
        buckets[day].append(deployment)
    trend: list[DORATrendPoint] = []
    for offset in range(window_days - 1, -1, -1):
        day = (now - timedelta(days=offset)).date().isoformat()
        deployments = buckets.get(day, [])
        day_lead_times = [
            item.lead_time_seconds
            for item in deployments
            if item.status == "succeeded" and item.lead_time_seconds is not None
        ]
        trend.append(
            DORATrendPoint(
                date=day,
                deployments=sum(item.status == "succeeded" for item in deployments),
                failures=sum(item.status in {"failed", "rolled_back"} for item in deployments),
                average_lead_time_seconds=round(mean(day_lead_times)) if day_lead_times else None,
            )
        )
    return DORAResponse(
        window_days=window_days,
        generated_at=now,
        service_slug=service_slug,
        summary=summary,
        trend=trend,
    )
