from __future__ import annotations

import os
from typing import Literal

AgentEnvironment = Literal["dev", "stage", "prod"]
ALLOWED_ENVS: set[str] = {"dev", "stage", "prod"}


def get_agent_environment() -> AgentEnvironment:
    value = os.getenv("AGENT_ENV", "dev").strip().lower()
    if value not in ALLOWED_ENVS:
        raise RuntimeError("AGENT_ENV must be one of: dev, stage, prod")
    return value
