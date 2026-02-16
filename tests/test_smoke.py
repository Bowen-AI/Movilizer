from pathlib import Path

from studio.utils import load_yaml


def test_workspace_file_exists() -> None:
    path = Path("workspace.yaml")
    assert path.exists()


def test_workspace_has_movie_project_reference() -> None:
    ws = load_yaml("workspace.yaml")
    assert ws["projects"]
    assert any(p["name"] == "feature_film_demo" for p in ws["projects"])
