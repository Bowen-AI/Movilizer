from pathlib import Path

from studio.models.registry import list_local_models, write_model_registry_index


def test_write_and_list_local_models(tmp_path: Path) -> None:
    model_dir = tmp_path / "models" / "toy_model"
    model_dir.mkdir(parents=True)
    (model_dir / "weights.bin").write_bytes(b"123")

    index_path = write_model_registry_index(tmp_path / "models")
    assert index_path.exists()

    listed = list_local_models(tmp_path / "models")
    assert listed
    assert any(item["name"] == "toy_model" for item in listed)
