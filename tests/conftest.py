"""Shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch, tmp_path: Path) -> Path:
    """Keep the default recipe file inside the test's temporary home."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.delenv("RECIPE_BOOK_DATA", raising=False)
    return home
