from studio.pipeline.executor import _apply_patch_ops


def test_patch_ops_prompt_and_cfg_changes() -> None:
    shot = {
        "shot_id": "shot_01",
        "generation": {"guidance_scale": 6.0},
        "references": {"wardrobe": "a"},
    }
    scene = {"scene_name": "scene_01"}
    dialog = {"lines": [{"line_id": "l1", "speaker": "narrator", "start_sec": 0.0, "end_sec": 1.0, "text": "hello"}]}

    ops = [
        {"op": "replace_prompt", "find": "straight hair", "replace": "wavy hair"},
        {"op": "set", "path": "generation.guidance_scale", "value": 7.0},
        {"op": "set_ref", "ref_path_key": "wardrobe", "value": "b"},
        {"op": "set_dialog_text", "speaker": "narrator", "line_id": "l1", "text": "updated"},
    ]

    shot2, scene2, dialog2, prompt2, neg2 = _apply_patch_ops(
        shot=shot,
        scene_data=scene,
        dialog_data=dialog,
        prompt="straight hair look",
        negative="low quality",
        ops=ops,
    )

    assert shot2["generation"]["guidance_scale"] == 7.0
    assert shot2["references"]["wardrobe"] == "b"
    assert "wavy hair" in prompt2
    assert neg2 == "low quality"
    assert dialog2["lines"][0]["text"] == "updated"
    assert scene2["_dialog_lines"][0]["text"] == "updated"
