from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=63, pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
    owner_team: str = Field(min_length=2, max_length=120)
    repository: AnyHttpUrl


class ServiceRead(ServiceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class DeploymentCreate(BaseModel):
    service_slug: str = Field(min_length=2, max_length=63)
    environment: Literal["production", "staging", "preview"]
    revision: str = Field(min_length=7, max_length=128, pattern=r"^[A-Za-z0-9._/-]+$")
    status: Literal["running", "succeeded", "failed", "rolled_back"] = "succeeded"
    source: Literal["api", "github", "argocd", "terraform"] = "api"
    change_kind: Literal["normal", "urgent"] = "normal"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    recovered_at: datetime | None = None
    lead_time_seconds: int | None = Field(default=None, ge=0, le=31_536_000)
    failure_reason: str | None = Field(default=None, max_length=1000)

    @field_validator("started_at", "finished_at", "recovered_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must include a timezone")
        return value


class DeploymentPatch(BaseModel):
    status: Literal["running", "succeeded", "failed", "rolled_back"] | None = None
    finished_at: datetime | None = None
    recovered_at: datetime | None = None
    failure_reason: str | None = Field(default=None, max_length=1000)


class DeploymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_slug: str
    environment: str
    revision: str
    status: str
    source: str
    change_kind: str
    started_at: datetime
    finished_at: datetime | None
    recovered_at: datetime | None
    lead_time_seconds: int | None
    failure_reason: str | None
    created_at: datetime


class DORASummary(BaseModel):
    deployment_frequency_per_week: float
    change_lead_time_p50_seconds: int | None
    change_lead_time_p95_seconds: int | None
    change_fail_rate_percent: float
    failed_deployment_recovery_p50_seconds: int | None
    deployment_rework_rate_percent: float


class DORATrendPoint(BaseModel):
    date: str
    deployments: int
    failures: int
    average_lead_time_seconds: int | None


class DORAResponse(BaseModel):
    window_days: int
    generated_at: datetime
    service_slug: str | None
    summary: DORASummary
    trend: list[DORATrendPoint]


class ErrorResponse(BaseModel):
    detail: str
