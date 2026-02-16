from datetime import datetime, timezone
from pathlib import Path
from time import sleep

from .models import ActionRequest, ActionResult

MAX_LIST_ENTRIES = 500


def execute_action_request(request: ActionRequest) -> ActionResult:
    if request.action == "vm.list_path":
        return _execute_vm_list_path(request)

    started_at = datetime.now(timezone.utc)

    sleep(0.3)

    return ActionResult(
        request_id=request.request_id,
        status="succeeded",
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        summary=f"Mock executed action '{request.action}' for environment '{request.environment}'",
        error=None,
    )


def _execute_vm_list_path(request: ActionRequest) -> ActionResult:
    started_at = datetime.now(timezone.utc)

    raw_path = request.params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("vm.list_path requires params.path as non-empty string")

    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"path is not a directory: {path}")

    names = sorted(
        f"{entry.name}/" if entry.is_dir() else entry.name for entry in path.iterdir()
    )
    total_entries = len(names)
    visible = names[:MAX_LIST_ENTRIES]
    preview = ", ".join(visible[:20]) if visible else "(empty)"
    truncated_note = " (truncated)" if total_entries > MAX_LIST_ENTRIES else ""

    return ActionResult(
        request_id=request.request_id,
        status="succeeded",
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        summary=(
            f"Listed {len(visible)}/{total_entries} entries under '{path}'{truncated_note}. "
            f"Preview: {preview}"
        ),
        error=None,
    )
