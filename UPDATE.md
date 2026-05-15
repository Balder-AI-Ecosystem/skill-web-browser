# UPDATE PLAN — skill-web-browser

> Audit date: 2026-04-21 | Grade: **B** | Priority: Medium

---

## Vấn đề tìm thấy

### 1. Schemas chưa khai báo properties (CRITICAL)
2 capabilities dùng schema rỗng. Fields thực tế: `target`, `dry_run`, `confirmed`, `confirmation_token`, `policy_approved`, `timeout_seconds`.

### 2. Capabilities có thể quá ít
Chỉ có 2 capabilities (`fetch` và `open_url`?). Web browser thường cần thêm: `navigate_back`, `get_current_url`, `take_screenshot`.

### 3. Test coverage tối thiểu
Chỉ manifest check. Không test adapter mock, timeout, invalid URL.

### 4. Dependencies không khai báo
`pyproject.toml` chỉ có `setuptools`. Dependency vào `BrowserToolAdapter` không được document.

---

## Fix cần làm

### Fix 1 — Cập nhật schemas (cần đọc actual capability IDs từ skill.yaml)

Pattern dựa trên implementation fields:

```yaml
# browser capability 1 (fetch / navigate)
input_schema:
  type: object
  required: [target]
  properties:
    target:
      type: string
      description: "URL to fetch or navigate to"
      format: uri
    dry_run:
      type: boolean
      default: false
    confirmed:
      type: boolean
      default: false
    confirmation_token:
      type: ["string", "null"]
    policy_approved:
      type: boolean
      default: false
    timeout_seconds:
      type: integer
      default: 30
      minimum: 5
      maximum: 120
  additionalProperties: false
output_schema:
  type: object
  required: [status]
  properties:
    status:
      type: string
      enum: [ok, error, timeout, confirmation_required]
    url:
      type: ["string", "null"]
      description: "Final URL after navigation (may differ from target due to redirects)"
    title: {type: ["string", "null"]}
    content: {type: ["string", "null"]}
    status_code: {type: ["integer", "null"]}
    preview: {type: object}
    confirmation_token: {type: ["string", "null"]}
    detail: {type: ["string", "null"]}
```

### Fix 2 — Thêm functional tests

```python
# tests/test_execute.py
from unittest.mock import MagicMock, patch

def make_req(capability_id, **params):
    req = MagicMock()
    req.capability_id = capability_id
    req.parameters = params
    return req

def test_fetch_url_dry_run():
    from src.skill_web_browser.main import Skill
    skill = Skill()
    # Get first capability ID from manifest
    cap_id = skill.manifest().capabilities[0].id
    result = skill.execute(make_req(cap_id, target="https://example.com", dry_run=True))
    assert result.get("status") in ("ok", "preview", "confirmation_required")

def test_fetch_url_adapter_error_returns_error_status():
    from src.skill_web_browser.main import Skill
    skill = Skill()
    cap_id = skill.manifest().capabilities[0].id
    with patch.object(skill, '_adapter') as mock_adapter:
        mock_adapter.fetch.side_effect = ConnectionError("Network error")
        result = skill.execute(make_req(cap_id, target="https://example.com"))
    assert result["status"] == "error"

def test_missing_target_raises():
    from src.skill_web_browser.main import Skill
    import pytest
    skill = Skill()
    cap_id = skill.manifest().capabilities[0].id
    with pytest.raises((ValueError, KeyError)):
        skill.execute(make_req(cap_id))  # no target
```

### Fix 3 — Document dependency

```toml
[project]
# Depends on BrowserToolAdapter from core ecosystem.
# Core must be on sys.path (injected by JARVIS loader).
dependencies = []  # runtime: ecosystem (injected by loader)
```

---

## Không cần làm
- `BrowserToolAdapter` integration pattern đúng
- `internet_access: true`, `external_actions: true` permissions đúng
- `confirmation_required: true` trên open/navigate actions đúng (side effects)
