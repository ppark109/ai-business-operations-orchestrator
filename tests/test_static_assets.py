from pathlib import Path


def test_css_has_no_patch_artifacts() -> None:
    css = Path("app/static/style.css").read_text(encoding="utf-8")

    assert "*** End Patch" not in css
    assert "*** Begin Patch" not in css
