import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


async def create_service(client: AsyncClient, slug: str = "checkout-api") -> dict:
    response = await client.post(
        "/api/v1/services",
        json={
            "name": "Checkout API",
            "slug": slug,
            "owner_team": "commerce-platform",
            "repository": "https://github.com/example/checkout-api",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_health_and_openapi(client: AsyncClient) -> None:
    live = await client.get("/health/live")
    ready = await client.get("/health/ready")
    assert live.json() == {"status": "ok"}
    assert ready.json() == {"status": "ready"}
    assert (await client.get("/openapi.json")).status_code == 200


@pytest.mark.asyncio
async def test_service_duplicate_is_conflict(client: AsyncClient) -> None:
    await create_service(client, "catalog-api")
    duplicate = await client.post(
        "/api/v1/services",
        json={
            "name": "Catalog API",
            "slug": "catalog-api",
            "owner_team": "catalog",
            "repository": "https://github.com/example/catalog-api",
        },
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_deployment_is_idempotent(client: AsyncClient) -> None:
    await create_service(client)
    payload = {
        "service_slug": "checkout-api",
        "environment": "production",
        "revision": "abc1234-release",
        "status": "succeeded",
        "source": "github",
        "lead_time_seconds": 1200,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    first = await client.post(
        "/api/v1/deployments", json=payload, headers={"Idempotency-Key": "delivery-1"}
    )
    second = await client.post(
        "/api/v1/deployments", json=payload, headers={"Idempotency-Key": "delivery-1"}
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len((await client.get("/api/v1/deployments?service_slug=checkout-api")).json()) == 1


@pytest.mark.asyncio
async def test_dora_metrics_and_audit_chain(client: AsyncClient) -> None:
    await create_service(client, "payments-api")
    now = datetime.now(UTC)
    for index, state in enumerate(["succeeded", "succeeded", "failed"]):
        finished = now - timedelta(days=index)
        payload = {
            "service_slug": "payments-api",
            "environment": "production",
            "revision": f"revision-{index}",
            "status": state,
            "lead_time_seconds": 600 + index * 100,
            "started_at": (finished - timedelta(minutes=10)).isoformat(),
            "finished_at": finished.isoformat(),
            "recovered_at": (finished + timedelta(minutes=30)).isoformat()
            if state == "failed"
            else None,
        }
        response = await client.post("/api/v1/deployments", json=payload)
        assert response.status_code == 201, response.text
    metrics = await client.get("/api/v1/metrics/dora?service_slug=payments-api")
    assert metrics.status_code == 200
    assert metrics.json()["summary"]["change_fail_rate_percent"] == pytest.approx(33.33, abs=0.01)
    events = (await client.get("/api/v1/audit?limit=20")).json()
    assert len(events) >= 4
    assert all(len(event["event_hash"]) == 64 for event in events)


@pytest.mark.asyncio
async def test_github_webhook_requires_valid_signature(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_service(client, "webhook-api")
    monkeypatch.setenv("DEPLOYLEDGER_WEBHOOK_SECRET", "test-secret")
    from app.config import get_settings

    get_settings.cache_clear()
    body = json.dumps({"repository": {"name": "webhook-api"}}).encode()
    signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    response = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={signature}", "X-GitHub-Event": "push"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "ignored"
    get_settings.cache_clear()
