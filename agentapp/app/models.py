from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ActionStatus = Literal["received", "running", "succeeded", "failed", "denied"]
ActionName = Literal[
    "docker.logs",
    "docker.restart_container",
    "k8s.pod_logs",
    "k8s.events",
    "k8s.scale_deployment",
    "jvm.status",
    "jvm.thread_dump",
    "vm.list_path",
    "vm.find_path",
    "vm.read_file",
    "service.restart",
]


class ActionRequest(BaseModel):
    request_id: UUID
    requested_at: datetime
    requested_by: str = Field(min_length=1)
    environment: Literal["dev", "stage", "prod"]
    action: ActionName
    target: dict[str, Any]
    params: dict[str, Any]


class ActionAccepted(BaseModel):
    request_id: UUID
    status: ActionStatus


class ActionResult(BaseModel):
    request_id: UUID
    status: ActionStatus
    started_at: datetime
    finished_at: datetime | None = None
    summary: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "agentapp"
    environment: Literal["dev", "stage", "prod"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
