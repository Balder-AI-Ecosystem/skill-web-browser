# skill-web-browser

Standalone web browser skill repo for lightweight fetch and open-url operations.

## Responsibility

This repo owns the simple browser boundary. It should cover read/open style browser actions, while heavier interactive browsing remains a separate boundary.

Capabilities declared in `skill.yaml`:

- `web_browser.fetch`
- `web_browser.open_url`

## Contract

- Mode: `local_plugin`
- Entrypoint: `src.skill_web_browser.main:Skill`
- Healthcheck: `src.skill_web_browser.main:healthcheck`
- Core API compatibility: `>=1.0,<2.0`

## Permissions

- `external_actions: true`
- `internet_access: true`
- `file_write: false`
- `read_memory: false`
- `write_memory: false`

## Integration rule

Core integration must stay at the skill boundary defined by `skill.yaml`. Interactive browser-session work should route to the browser-session skill, not be added to this repo implicitly.
## Verification

- Recommended command: `python -m pytest -q`
- Current minimum coverage: manifest and contract smoke tests inside `tests/`

## Implementation status

This repo currently acts as a controlled bridge around existing browser fetch/open behavior. The important constraint is that core consumes it only through the declared plugin contract.

Current dependency note: the runtime path still resolves the core repo location, so implementation independence is not complete yet.
