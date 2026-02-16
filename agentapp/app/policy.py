from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import yaml

from .models import ActionName

DEFAULT_POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "policy.yaml"


class PolicyEngine:
    def __init__(self, policy_path: Path | None = None) -> None:
        self._policy_path = policy_path or DEFAULT_POLICY_PATH
        self._lock = Lock()
        self._policy: dict[str, Any] | None = None
        self._last_mtime_ns: int | None = None
        self._last_reload_at: datetime | None = None
        self._load_error: str | None = None
        self._version: int | str | None = None

    def evaluate(self, action: ActionName, environment: str) -> tuple[bool, str]:
        self._reload_if_needed()

        if self._policy is None:
            return False, self._load_error or "policy unavailable"

        environments = self._policy.get("environments", {})
        env_policy = environments.get(environment, {})
        allow = set(env_policy.get("allow", []))
        deny = set(env_policy.get("deny", []))

        if "*" in deny or action in deny:
            return False, "denied by policy deny list"

        if "*" in allow or action in allow:
            return True, "allowed"

        return False, "action not allowed in environment"

    def policy_path(self) -> Path:
        return self._policy_path

    def status(self) -> dict[str, Any]:
        self._reload_if_needed()
        return {
            "loaded": self._policy is not None,
            "version": self._version,
            "source": "local_yaml",
            "last_reload_at": self._last_reload_at.isoformat() if self._last_reload_at else None,
            "error": self._load_error,
        }

    def _reload_if_needed(self) -> None:
        with self._lock:
            try:
                stat = self._policy_path.stat()
            except FileNotFoundError:
                self._policy = None
                self._last_mtime_ns = None
                self._last_reload_at = datetime.now(timezone.utc)
                self._version = None
                self._load_error = "policy file not found"
                return

            if self._last_mtime_ns == stat.st_mtime_ns and self._policy is not None:
                return

            try:
                raw = yaml.safe_load(self._policy_path.read_text(encoding="utf-8"))
            except Exception as exc:
                self._policy = None
                self._last_mtime_ns = stat.st_mtime_ns
                self._last_reload_at = datetime.now(timezone.utc)
                self._version = None
                self._load_error = f"failed to parse policy file: {exc}"
                return

            if not isinstance(raw, dict):
                self._policy = None
                self._last_mtime_ns = stat.st_mtime_ns
                self._last_reload_at = datetime.now(timezone.utc)
                self._version = None
                self._load_error = "policy file must be a YAML object"
                return

            environments = raw.get("environments")
            if not isinstance(environments, dict):
                self._policy = None
                self._last_mtime_ns = stat.st_mtime_ns
                self._last_reload_at = datetime.now(timezone.utc)
                self._version = None
                self._load_error = "policy file must define 'environments' object"
                return

            self._policy = raw
            self._last_mtime_ns = stat.st_mtime_ns
            self._last_reload_at = datetime.now(timezone.utc)
            version = raw.get("version")
            if isinstance(version, (int, str)):
                self._version = version
            else:
                self._version = None
            self._load_error = None
