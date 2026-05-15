"""Functional tests for Skill.execute (manifest capability IDs and adapter wiring)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from skill_web_browser.main import Skill


def _make_request(task_id: str, capability: str, parameters: dict | None) -> MagicMock:
    req = MagicMock()
    req.task_id = task_id
    req.capability = capability
    req.parameters = parameters
    return req


def test_fetch_url_dry_run() -> None:
    skill = Skill()
    mock_adapter = MagicMock()
    mock_adapter.execute.return_value = {"status": "preview", "detail": "dry run"}
    skill._adapter = mock_adapter

    result = skill.execute(
        _make_request(
            "t-dry-run",
            "web_browser.fetch",
            {"target": "https://example.com", "dry_run": True},
        )
    )
    assert result.status == "preview"
    mock_adapter.execute.assert_called_once()


def test_fetch_url_adapter_error_payload_maps_to_failed() -> None:
    skill = Skill()
    mock_adapter = MagicMock()
    mock_adapter.execute.return_value = {"status": "error", "detail": "Network error"}
    skill._adapter = mock_adapter

    result = skill.execute(
        _make_request("t-err", "web_browser.fetch", {"target": "https://example.com"}),
    )
    assert result.status == "failed"


def test_missing_target_raises() -> None:
    skill = Skill()
    with pytest.raises(ValueError, match="target"):
        skill.execute(_make_request("t-missing", "web_browser.fetch", {}))
