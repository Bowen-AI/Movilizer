from __future__ import annotations

from typing import Any


def _to_int_pair(value: Any) -> tuple[int, int] | None:
    if isinstance(value, list) and len(value) == 2:
        try:
            return (int(value[0]), int(value[1]))
        except Exception:
            return None
    return None


def apply_run_profile_overrides(compiled_shots: list[Any], run_config: dict[str, Any]) -> None:
    local_debug = run_config.get("local_debug", {}) if isinstance(run_config, dict) else {}
    if not isinstance(local_debug, dict) or not bool(local_debug.get("enabled", False)):
        return

    max_fps = int(local_debug.get("max_fps", 12))
    resolution = _to_int_pair(local_debug.get("resolution"))
    duration_scale = float(local_debug.get("duration_scale", 1.0))
    max_frames = int(local_debug.get("max_frames_per_shot", 0))
    max_steps = int(local_debug.get("max_inference_steps", 0))

    for compiled in compiled_shots:
        shot = compiled.shot_data
        fps = int(shot.get("fps", 24))
        shot["fps"] = min(fps, max_fps)

        if resolution:
            shot["resolution"] = [resolution[0], resolution[1]]

        duration = float(shot.get("duration", 1.0))
        if duration_scale > 0:
            duration = max(0.3, duration * duration_scale)

        if max_frames > 0 and shot["fps"] > 0:
            max_duration = max_frames / float(shot["fps"])
            duration = min(duration, max_duration)
        shot["duration"] = duration

        generation = shot.get("generation", {})
        if not isinstance(generation, dict):
            generation = {}

        if max_steps > 0:
            cur_steps = int(generation.get("num_inference_steps", max_steps))
            generation["num_inference_steps"] = min(cur_steps, max_steps)

        shot["generation"] = generation

        # keep CompiledShot.frame_count consistent with modified fps/duration
        compiled.frame_count = max(1, int(round(float(shot.get("duration", 1.0)) * float(shot.get("fps", 24)))))
