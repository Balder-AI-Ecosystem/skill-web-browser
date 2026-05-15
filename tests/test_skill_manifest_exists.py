from skill_web_browser.main import Skill


def test_skill_manifest_exists() -> None:
    manifest = Skill().manifest()

    assert manifest.name == "skill-web-browser"
    assert "web_browser.fetch" in manifest.capability_ids()
    assert "web_browser.open_url" in manifest.capability_ids()
