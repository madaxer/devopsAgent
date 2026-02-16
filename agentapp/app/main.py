from datetime import datetime, timezone
from threading import Thread
from uuid import UUID

from fastapi import FastAPI, HTTPException

from .executor import execute_action_request
from .models import ActionAccepted, ActionRequest, ActionResult, HealthResponse
from .policy import PolicyEngine
from .settings import get_agent_environment
from .store import ActionStore

app = FastAPI(title="DevOps AI Agent", version="0.1.0")
store = ActionStore()
policy_engine = PolicyEngine()
agent_environment = get_agent_environment()


def _run_action(request: ActionRequest) -> None:
    try:
        result = execute_action_request(request)
        store.upsert(result)
    except Exception as exc:
        failed = ActionResult(
            request_id=request.request_id,
            status="failed",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            summary=None,
            error=str(exc),
        )
        store.upsert(failed)


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(environment=agent_environment)


@app.get("/v1/policy/status")
def policy_status() -> dict[str, object]:
    status = policy_engine.status()
    status["agent_environment"] = agent_environment
    return status


@app.post("/v1/actions/execute", response_model=ActionAccepted, status_code=202)
def execute_action(request: ActionRequest) -> ActionAccepted:
    if request.environment != agent_environment:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "environment_mismatch",
                "expected_environment": agent_environment,
                "provided_environment": request.environment,
            },
        )

    existing = store.get(request.request_id)
    if existing is not None:
        if existing.status == "denied":
            raise HTTPException(
                status_code=403,
                detail={
                    "decision": "denied",
                    "policy": existing.error or "denied by policy",
                },
            )
        return ActionAccepted(request_id=request.request_id, status=existing.status)

    is_allowed, policy_message = policy_engine.evaluate(request.action, agent_environment)
    if not is_allowed:
        denied = ActionResult(
            request_id=request.request_id,
            status="denied",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            summary="Denied by policy",
            error=policy_message,
        )
        store.upsert(denied)
        raise HTTPException(
            status_code=403,
            detail={
                "decision": "denied",
                "policy": policy_message,
            },
        )

    running = ActionResult(
        request_id=request.request_id,
        status="running",
        started_at=datetime.now(timezone.utc),
        summary=None,
        error=None,
    )
    store.upsert(running)

    worker = Thread(target=_run_action, args=(request,), daemon=True)
    worker.start()

    return ActionAccepted(request_id=request.request_id, status="running")


@app.get("/v1/actions/{request_id}", response_model=ActionResult)
def get_action_status(request_id: UUID) -> ActionResult:
    result = store.get(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="request_id not found")
    return result
