from studio.ai_cmd.rules_backend import plan_from_rules


def test_rules_parser_extracts_scene_shot_and_frame_range() -> None:
    req = "Make scene_01 shot_03 more cinematic; regenerate only frames 120-220 and set cfg 7.2"
    plan = plan_from_rules(req, {"project": "my_makeover", "scene": None, "shot": None}, dry_run=True)

    assert plan.context["scene"] == "scene_01"
    assert plan.context["shot"] == "shot_03"
    assert any(a.type == "apply_patch" for a in plan.actions)
    patch_action = next(a for a in plan.actions if a.type == "apply_patch")
    ops = patch_action.payload["ops"]
    assert any(op.get("op") == "set_frame_range" and op.get("value") == [120, 220] for op in ops)
    assert any(op.get("path") == "generation.guidance_scale" and op.get("value") == 7.2 for op in ops)
