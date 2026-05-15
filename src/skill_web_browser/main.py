from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any


def _is_core_repo(candidate: Path) -> bool:
    return candidate.is_dir() and (candidate / "pyproject.toml").is_file() and (candidate / "ecosystem").is_dir()


def _candidate_core_repos() -> list[Path]:
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[2]
    candidates: list[Path] = []

    configured = str(os.getenv("AUTOBOT_CORE_REPO", "")).strip()
    if configured:
        candidates.append(Path(configured).expanduser())

    for anchor in (current_file.parent, Path.cwd().resolve()):
        candidates.extend([anchor, *anchor.parents])

    parent_dir = repo_root.parent
    if parent_dir.exists():
        candidates.extend(path for path in parent_dir.iterdir() if path.is_dir())

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def _default_core_repo() -> Path:
    for candidate in _candidate_core_repos():
        if _is_core_repo(candidate):
            return candidate
    raise RuntimeError("Unable to locate the core repo. Set AUTOBOT_CORE_REPO to a valid core repo path.")


def _ensure_core_repo_on_path() -> Path:
    candidate = _default_core_repo()
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
    return candidate


_CORE_REPO = _ensure_core_repo_on_path()

from ecosystem.contracts import HealthSnapshot, TaskRequest, TaskResult  # noqa: E402
from ecosystem.skills import BaseSkill, SkillCapability, SkillManifest  # noqa: E402

if TYPE_CHECKING:
    from ecosystem.domains.desktop_control.browser_tool_adapter import BrowserToolAdapter


def _map_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"completed", "success", "ok"}:
        return "completed"
    if normalized in {"blocked", "needs_confirmation", "awaiting_confirmation"}:
        return "blocked"
    if normalized in {"preview", "dry_run"}:
        return "preview"
    return "failed"


_CAPABILITY_TO_ACTION = {
    "web_browser.fetch": "fetch",
    "web_browser.open_url": "open_url",
}

_BROWSER_CAPABILITY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["target"],
    "properties": {
        "target": {
            "type": "string",
            "description": "URL to fetch or navigate to",
            "format": "uri",
        },
        "dry_run": {"type": "boolean", "default": False},
        "confirmed": {"type": "boolean", "default": False},
        "confirmation_token": {"type": ["string", "null"]},
        "policy_approved": {"type": "boolean", "default": False},
        "timeout_seconds": {"type": "integer", "default": 30, "minimum": 5, "maximum": 120},
    },
    "additionalProperties": False,
}

_BROWSER_CAPABILITY_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["status"],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["ok", "error", "timeout", "confirmation_required"],
        },
        "url": {
            "type": ["string", "null"],
            "description": "Final URL after navigation (may differ from target due to redirects)",
        },
        "title": {"type": ["string", "null"]},
        "content": {"type": ["string", "null"]},
        "status_code": {"type": ["integer", "null"]},
        "preview": {"type": "object"},
        "confirmation_token": {"type": ["string", "null"]},
        "detail": {"type": ["string", "null"]},
    },
}


class Skill(BaseSkill):
    def __init__(self, adapter: "BrowserToolAdapter" | None = None) -> None:
        self._adapter = adapter

    @property
    def adapter(self) -> "BrowserToolAdapter":
        if self._adapter is None:
            from ecosystem.domains.desktop_control.browser_tool_adapter import BrowserToolAdapter

            self._adapter = BrowserToolAdapter()
        return self._adapter

    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="skill-web-browser",
            version="0.1.0",
            mode="local_plugin",
            entrypoint="src.skill_web_browser.main:Skill",
            core_api=">=1.0,<2.0",
            capabilities=[
                SkillCapability(
                    id="web_browser.fetch",
                    description="Fetch a browser target and extract readable content.",
                    input_schema=_BROWSER_CAPABILITY_INPUT_SCHEMA,
                    output_schema=_BROWSER_CAPABILITY_OUTPUT_SCHEMA,
                    retry_policy="bounded_backoff",
                    observability_events=["web_browser.fetch"],
                ),
                SkillCapability(
                    id="web_browser.open_url",
                    description="Open a browser URL or local file in the user's browser.",
                    input_schema=_BROWSER_CAPABILITY_INPUT_SCHEMA,
                    output_schema=_BROWSER_CAPABILITY_OUTPUT_SCHEMA,
                    retry_policy="bounded_backoff",
                    observability_events=["web_browser.open_url"],
                ),
            ],
            permissions={
                "read_memory": False,
                "write_memory": False,
                "internet_access": True,
                "file_write": False,
                "external_actions": True,
            },
            healthcheck={"kind": "python", "target": "src.skill_web_browser.main:healthcheck"},
            timeout_ms=60000,
            enabled_by_default=True,
        )

    def healthcheck(self) -> HealthSnapshot:
        return HealthSnapshot(
            status="healthy",
            available=True,
            updated_at=None,
            detail="Web browser adapter is available.",
            counters={},
            evidence={"bridge_mode": True},
        )

    def execute(self, request: TaskRequest) -> TaskResult:
        capability = str(request.capability or "").strip()
        if capability not in _CAPABILITY_TO_ACTION:
            raise ValueError(f"Unsupported capability: {capability}")
        from ecosystem.domains.desktop_control.software_tool_models import ToolActionRequest

        target = str((request.parameters or {}).get("target") or "").strip()
        if not target:
            raise ValueError("target is required")

        tool_request = ToolActionRequest(
            adapter_name="web_browser",
            action=_CAPABILITY_TO_ACTION[capability],
            target=target,
            parameters=dict(request.parameters or {}),
            policy_approved=bool((request.parameters or {}).get("policy_approved", True)),
            timeout_seconds=int((request.parameters or {}).get("timeout_seconds") or 30),
        )
        payload = self.adapter.execute(tool_request)
        return TaskResult(
            task_id=request.task_id,
            status=_map_status(payload.get("status")),
            detail=str(payload.get("detail") or payload.get("status") or "Skill execution finished."),
            failure_category=str(payload.get("failure_category") or "").strip() or None,
            artifacts={"result": payload},
            evidence={"bridge_mode": True},
            next_actions=list(payload.get("next_actions") or []),
            module_name="skill-web-browser",
            capability=request.capability,
        )


def healthcheck() -> dict[str, Any]:
    return Skill().healthcheck().as_dict()
