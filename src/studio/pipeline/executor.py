from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import LoadedProject
from ..media.audio import audio_stats, mix_dialog_and_music
from ..media.music import render_music_track
from ..media.tts import render_dialog_track, write_srt
from ..media.video import concat_clips, frames_to_clip, mux_audio
from ..models.adapters import make_reference_adapter
from ..models.diffusion import DiffusionConfig, DiffusionGenerator
from ..models.lora import lora_checksum
from ..prompts.composer import apply_prompt_mutations, compose_negative_prompt, compose_prompt
from ..utils import (
    ensure_dir,
    get_git_hash,
    get_logger,
    load_json,
    load_yaml,
    now_utc_iso,
    save_json,
    save_yaml,
    stable_hash,
    write_text,
)
from .cache import compute_signature, should_skip, update_task_signature

logger = get_logger("pipeline.executor")


@dataclass
class CompiledShot:
    project: str
    scene: str
    shot_id: str
    scene_data: dict[str, Any]
    shot_data: dict[str, Any]
    dialog_data: dict[str, Any]
    compiled_prompt: str
    compiled_negative_prompt: str
    output_dir: Path
    compiled_dir: Path
    frame_count: int
    frame_range: tuple[int, int] | None
    patch_files: list[str]
    compiled_hash: str
    visual_hash: str
    audio_hash: str


def _set_path(payload: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _delete_path(payload: dict[str, Any], dotted: str) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            return
        cursor = cursor[part]
    cursor.pop(parts[-1], None)


def _append_path(payload: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    arr = cursor.get(parts[-1])
    if not isinstance(arr, list):
        arr = []
        cursor[parts[-1]] = arr
    arr.append(value)


def _extend_path(payload: dict[str, Any], dotted: str, values: list[Any]) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    arr = cursor.get(parts[-1])
    if not isinstance(arr, list):
        arr = []
        cursor[parts[-1]] = arr
    arr.extend(values)


def _parse_frame_range(value: Any) -> tuple[int, int] | None:
    if isinstance(value, list) and len(value) == 2:
        start = max(0, int(value[0]))
        end = max(start, int(value[1]))
        return (start, end)
    if isinstance(value, dict):
        start = int(value.get("start", 0))
        end = int(value.get("end", start))
        return (max(0, start), max(start, end))
    if isinstance(value, str) and "-" in value:
        left, right = value.split("-", 1)
        if left.isdigit() and right.isdigit():
            start = int(left)
            end = int(right)
            return (max(0, start), max(start, end))
    return None


def _apply_audio_op(dialog: dict[str, Any], scene: dict[str, Any], op: dict[str, Any]) -> None:
    opname = op.get("op")
    lines = scene.get("_dialog_lines", dialog.get("lines", []))

    if opname == "set_dialog_text":
        speaker = str(op.get("speaker", ""))
        line_id = str(op.get("line_id", ""))
        text = str(op.get("text", ""))
        for line in lines:
            if str(line.get("line_id")) == line_id and (not speaker or str(line.get("speaker")) == speaker):
                line["text"] = text

    elif opname == "shift_dialog_time":
        line_id = str(op.get("line_id", ""))
        delta = float(op.get("delta_seconds", 0.0))
        for line in lines:
            if str(line.get("line_id")) == line_id:
                line["start_sec"] = max(0.0, float(line.get("start_sec", 0.0)) + delta)
                line["end_sec"] = max(float(line["start_sec"]) + 0.05, float(line.get("end_sec", 0.0)) + delta)

    elif opname == "replace_music":
        scene["music_override"] = str(op.get("track_path", ""))

    scene["_dialog_lines"] = lines


def _apply_patch_ops(
    shot: dict[str, Any],
    scene_data: dict[str, Any],
    dialog_data: dict[str, Any],
    prompt: str,
    negative: str,
    ops: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    shot_out = dict(shot)
    scene_out = dict(scene_data)
    dialog_out = dict(dialog_data)

    prompt_ops: list[dict[str, Any]] = []
    for op in ops:
        name = op.get("op")
        if name in {
            "replace_prompt",
            "add_prompt_prefix",
            "add_prompt_suffix",
            "add_negative_prefix",
            "add_negative_suffix",
        }:
            prompt_ops.append(op)
            continue

        if name == "set":
            _set_path(shot_out, str(op.get("path", "")), op.get("value"))
        elif name == "delete":
            _delete_path(shot_out, str(op.get("path", "")))
        elif name == "append":
            _append_path(shot_out, str(op.get("path", "")), op.get("value"))
        elif name == "extend":
            _extend_path(shot_out, str(op.get("path", "")), list(op.get("values", [])))
        elif name == "set_ref":
            refs = shot_out.get("references", {})
            if not isinstance(refs, dict):
                refs = {}
            refs[str(op.get("ref_path_key", "ref"))] = op.get("value")
            shot_out["references"] = refs
        elif name == "set_frame_range":
            fr = _parse_frame_range(op.get("value"))
            if fr:
                gen = shot_out.get("generation", {})
                if not isinstance(gen, dict):
                    gen = {}
                gen["frame_range"] = [fr[0], fr[1]]
                shot_out["generation"] = gen
        elif name in {"set_dialog_text", "shift_dialog_time", "replace_music"}:
            _apply_audio_op(dialog_out, scene_out, op)

    prompt_out, negative_out = apply_prompt_mutations(prompt, negative, prompt_ops)
    return shot_out, scene_out, dialog_out, prompt_out, negative_out


def _resolve_path(root: Path, path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (root / p).resolve()


def _load_patch_file(patch_path: Path) -> dict[str, Any]:
    return load_yaml(patch_path)


def _patches_for_target(
    patch_paths: list[Path],
    project: str,
    scene: str,
    shot: str,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for patch_path in sorted(patch_paths):
        patch = _load_patch_file(patch_path)
        target = patch.get("target", {})
        if target.get("project") and str(target.get("project")) != project:
            continue
        if target.get("scene") and str(target.get("scene")) != scene:
            continue
        if target.get("shot") and str(target.get("shot")) != shot:
            continue
        selected.append({"path": str(patch_path), "data": patch})
    return selected


def _prompt_for_frame(base_prompt: str, prompt_schedule: list[dict[str, Any]], frame_idx: int) -> str:
    if not prompt_schedule:
        return base_prompt
    current_suffix = ""
    for item in sorted(prompt_schedule, key=lambda x: int(x.get("frame", 0))):
        if frame_idx >= int(item.get("frame", 0)):
            current_suffix = str(item.get("prompt_suffix", ""))
    if current_suffix:
        return f"{base_prompt} {current_suffix}".strip()
    return base_prompt


def compile_scene(
    workspace: dict[str, Any],
    project: LoadedProject,
    scene_path: Path,
    run_id: str,
    output_root: Path,
    selected_shot_ids: list[str] | None,
    patch_paths: list[Path],
) -> tuple[list[CompiledShot], dict[str, Any], dict[str, Any]]:
    ws_dir = Path(workspace["_workspace_dir"])  # repository root
    project_root = project.path.parent

    scene_data = load_yaml(scene_path)
    scene_name = str(scene_data.get("scene_name", scene_path.stem))

    dialog_ref = scene_data.get("dialog_ref")
    if dialog_ref:
        dialog_path = _resolve_path(ws_dir, str(dialog_ref))
        dialog_data = load_yaml(dialog_path)
    else:
        dialog_path = None
        dialog_data = {"lines": [], "speakers": {}}

    global_guidelines = workspace.get("global_guidelines", {})
    global_prompt = str(global_guidelines.get("prompt", ""))
    global_negative = str(global_guidelines.get("negative_prompt", ""))

    project_vibes = project.data.get("style_bible", {}).get("vibe_guidelines", [])
    project_vibe = ", ".join(str(x) for x in project_vibes)
    scene_vibe = str(scene_data.get("vibe_overrides", {}).get("prompt", ""))
    scene_negative = str(scene_data.get("vibe_overrides", {}).get("negative_prompt", ""))

    template_path = project_root / "scripts" / "prompt_templates" / "default_prompt.j2"
    compiled: list[CompiledShot] = []

    shots = scene_data.get("shots", [])
    for shot in shots:
        shot_id = str(shot.get("shot_id"))
        if selected_shot_ids and shot_id not in selected_shot_ids:
            continue

        shot_prompt = str(shot.get("prompt", ""))
        shot_negative = str(shot.get("negative_prompt", ""))
        refs = shot.get("references", {}) if isinstance(shot.get("references"), dict) else {}

        prompt = compose_prompt(
            global_guidelines=global_prompt,
            project_vibe=project_vibe,
            scene_vibe=scene_vibe,
            shot_prompt=shot_prompt,
            camera=str(shot.get("camera", "")),
            lens=str(shot.get("lens", "")),
            lighting=str(shot.get("lighting", "")),
            wardrobe=str(refs.get("wardrobe", "")),
            location=str(refs.get("background", scene_data.get("location_refs", [""])[0] if scene_data.get("location_refs") else "")),
            template_path=str(template_path) if template_path.exists() else None,
        )
        negative = compose_negative_prompt(global_negative, scene_negative, shot_negative)

        shot_scene = dict(scene_data)
        shot_dialog = dict(dialog_data)

        target_patches = _patches_for_target(
            patch_paths=patch_paths,
            project=project.name,
            scene=scene_name,
            shot=shot_id,
        )

        for patch in target_patches:
            ops = patch["data"].get("ops", [])
            shot, shot_scene, shot_dialog, prompt, negative = _apply_patch_ops(
                shot=shot,
                scene_data=shot_scene,
                dialog_data=shot_dialog,
                prompt=prompt,
                negative=negative,
                ops=ops,
            )

        out_dir = output_root / run_id / project.name / scene_name / shot_id
        compiled_dir = out_dir / "compiled"
        ensure_dir(compiled_dir)

        old_prompt = (compiled_dir / "compiled_prompt.txt").read_text(encoding="utf-8") if (compiled_dir / "compiled_prompt.txt").exists() else ""
        if old_prompt:
            diff = difflib.unified_diff(
                old_prompt.splitlines(),
                prompt.splitlines(),
                fromfile="previous",
                tofile="current",
                lineterm="",
            )
            write_text(compiled_dir / "compiled_prompt.diff.txt", "\n".join(diff) + "\n")
        else:
            write_text(compiled_dir / "compiled_prompt.diff.txt", "(no previous prompt for diff)\n")

        frame_count = max(1, int(round(float(shot.get("duration", 1.0)) * float(shot.get("fps", 24)))))
        fr = shot.get("generation", {}).get("frame_range")
        frame_range = _parse_frame_range(fr) if fr is not None else None

        model_cfg = project.data.get("model", {})
        lora_checksums = []
        for lora in model_cfg.get("loras", []):
            path = lora.get("path")
            if path:
                checksum = lora_checksum(_resolve_path(ws_dir, str(path)))
                if checksum:
                    lora_checksums.append({"path": path, "sha256": checksum})

        provenance = {
            "timestamp_utc": now_utc_iso(),
            "git_hash": get_git_hash(),
            "workspace_path": workspace.get("_workspace_path"),
            "project_yaml": str(project.path),
            "scene_yaml": str(scene_path),
            "dialog_yaml": str(dialog_path) if dialog_path else None,
            "model_ids": {
                "base": model_cfg.get("base_id"),
                "refiner": model_cfg.get("refiner_id"),
                "use_refiner": model_cfg.get("use_refiner", False),
            },
            "lora_checksums": lora_checksums,
        }

        compiled_meta = {
            "project": project.name,
            "scene": scene_name,
            "shot": shot_id,
            "patches": [p["path"] for p in target_patches],
            "frame_count": frame_count,
            "frame_range": list(frame_range) if frame_range else None,
            "provenance": provenance,
        }
        visual_hash = stable_hash(
            {
                "shot": shot,
                "prompt": prompt,
                "negative": negative,
                "refs": shot.get("references", {}),
                "generation": shot.get("generation", {}),
            }
        )
        audio_hash = stable_hash(
            {
                "scene_music_override": shot_scene.get("music_override"),
                "dialog_lines": shot_dialog.get("lines", []),
            }
        )
        compiled_hash = stable_hash(
            {"visual_hash": visual_hash, "audio_hash": audio_hash, "meta": compiled_meta}
        )
        compiled_meta["compiled_hash"] = compiled_hash
        compiled_meta["visual_hash"] = visual_hash
        compiled_meta["audio_hash"] = audio_hash

        save_yaml(compiled_dir / "compiled_scene.yaml", shot_scene)
        save_yaml(compiled_dir / "compiled_shot.yaml", shot)
        write_text(compiled_dir / "compiled_prompt.txt", prompt + "\n")
        write_text(compiled_dir / "compiled_negative_prompt.txt", negative + "\n")
        save_json(compiled_dir / "compiled_metadata.json", compiled_meta)

        compiled.append(
            CompiledShot(
                project=project.name,
                scene=scene_name,
                shot_id=shot_id,
                scene_data=shot_scene,
                shot_data=shot,
                dialog_data=shot_dialog,
                compiled_prompt=prompt,
                compiled_negative_prompt=negative,
                output_dir=out_dir,
                compiled_dir=compiled_dir,
                frame_count=frame_count,
                frame_range=frame_range,
                patch_files=[p["path"] for p in target_patches],
                compiled_hash=compiled_hash,
                visual_hash=visual_hash,
                audio_hash=audio_hash,
            )
        )

    return compiled, scene_data, dialog_data


def _resolve_requested_frame_indices(compiled: CompiledShot) -> list[int]:
    all_indices = list(range(compiled.frame_count))
    frames_dir = compiled.output_dir / "frames"

    if not compiled.frame_range:
        return all_indices

    start, end = compiled.frame_range
    start = max(0, min(start, compiled.frame_count - 1))
    end = max(start, min(end, compiled.frame_count - 1))

    requested = set(range(start, end + 1))
    existing = {
        int(p.stem.split("_")[-1])
        for p in frames_dir.glob("frame_*.png")
        if p.stem.split("_")[-1].isdigit()
    }
    missing = {idx for idx in all_indices if idx not in existing}
    return sorted(requested | missing)


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return True


def execute_compiled_scene(
    workspace: dict[str, Any],
    project: LoadedProject,
    scene_name: str,
    compiled_shots: list[CompiledShot],
    output_root: Path,
    run_id: str,
    resume: bool,
    compile_only: bool,
) -> None:
    if not compiled_shots:
        return

    ws_dir = Path(workspace["_workspace_dir"])
    run_generation_cfg = workspace.get("global_defaults", {}).get("run_settings", {})
    model_cfg_data = project.data.get("model", workspace.get("global_defaults", {}).get("model", {}))

    diff_cfg = DiffusionConfig(
        base_id=str(model_cfg_data.get("base_id", "stabilityai/stable-diffusion-xl-base-1.0")),
        refiner_id=str(model_cfg_data.get("refiner_id", "")) or None,
        use_refiner=bool(model_cfg_data.get("use_refiner", False)),
        precision=str(model_cfg_data.get("precision", "bf16")),
        enable_xformers=bool(model_cfg_data.get("enable_xformers", True)),
        attention_slicing=bool(model_cfg_data.get("attention_slicing", True)),
    )

    generator = DiffusionGenerator(diff_cfg)
    ref_adapter = make_reference_adapter(project.data.get("reference_adapter", {"name": "noop"}))

    scene_out_dir = output_root / run_id / project.name / scene_name
    ensure_dir(scene_out_dir)

    scene_clip_paths: list[Path] = []
    scene_dialog_data = compiled_shots[0].dialog_data
    scene_data = compiled_shots[0].scene_data

    for compiled in compiled_shots:
        frames_dir = compiled.output_dir / "frames"
        ensure_dir(frames_dir)
        clip_path = compiled.output_dir / "clip.mp4"

        frame_indices = _resolve_requested_frame_indices(compiled)

        frame_signature = compute_signature(
            {
                "visual_hash": compiled.visual_hash,
                "frame_indices": frame_indices,
                "model": model_cfg_data,
                "generation": compiled.shot_data.get("generation", {}),
                "run_generation_cfg": run_generation_cfg,
                "code_git": get_git_hash(),
            }
        )

        skip_frames = should_skip(
            compiled_dir=compiled.compiled_dir,
            task_key="frames",
            signature=frame_signature,
            required_outputs=[frames_dir / f"frame_{i:06d}.png" for i in range(compiled.frame_count)],
            resume=resume,
        )

        if compile_only:
            logger.info("Compile-only mode: skipping render for %s/%s/%s", compiled.project, compiled.scene, compiled.shot_id)
            continue

        if not skip_frames:
            logger.info("Generating %s frames for %s/%s/%s", len(frame_indices), compiled.project, compiled.scene, compiled.shot_id)
            prompt_schedule = compiled.shot_data.get("generation", {}).get("prompt_schedule", [])
            refs = compiled.shot_data.get("references", {})

            for frame_idx in frame_indices:
                prompt_frame = _prompt_for_frame(compiled.compiled_prompt, prompt_schedule, frame_idx)
                gen_kwargs = ref_adapter.apply({}, refs)
                generator.generate_frame(
                    prompt=prompt_frame,
                    negative_prompt=compiled.compiled_negative_prompt,
                    seed=int(compiled.shot_data.get("generation", {}).get("seed", 0)),
                    width=int(compiled.shot_data.get("resolution", [1024, 1024])[0]),
                    height=int(compiled.shot_data.get("resolution", [1024, 1024])[1]),
                    output_path=frames_dir / f"frame_{frame_idx:06d}.png",
                    frame_idx=frame_idx,
                    generation_kwargs=gen_kwargs,
                )
            update_task_signature(compiled.compiled_dir, "frames", frame_signature)
        else:
            logger.info("Skipping frame generation (cache hit) for %s/%s/%s", compiled.project, compiled.scene, compiled.shot_id)

        clip_signature = compute_signature(
            {
                "frame_signature": frame_signature,
                "fps": compiled.shot_data.get("fps", 24),
                "frame_count": compiled.frame_count,
            }
        )
        if should_skip(
            compiled_dir=compiled.compiled_dir,
            task_key="clip",
            signature=clip_signature,
            required_outputs=[clip_path],
            resume=resume,
        ):
            logger.info("Skipping clip assembly (cache hit) for %s/%s/%s", compiled.project, compiled.scene, compiled.shot_id)
        else:
            frames_to_clip(frames_dir=frames_dir, fps=int(compiled.shot_data.get("fps", 24)), output_path=clip_path)
            update_task_signature(compiled.compiled_dir, "clip", clip_signature)

        metadata = {
            "project": compiled.project,
            "scene": compiled.scene,
            "shot": compiled.shot_id,
            "compiled_prompt": compiled.compiled_prompt,
            "compiled_negative_prompt": compiled.compiled_negative_prompt,
            "patches": compiled.patch_files,
            "frame_count": compiled.frame_count,
            "frame_range": list(compiled.frame_range) if compiled.frame_range else None,
            "references": compiled.shot_data.get("references", {}),
            "generation": compiled.shot_data.get("generation", {}),
            "provenance": {
                "git_hash": get_git_hash(),
                "compiled_hash": compiled.compiled_hash,
                "model_ids": {
                    "base_id": model_cfg_data.get("base_id"),
                    "refiner_id": model_cfg_data.get("refiner_id"),
                    "use_refiner": model_cfg_data.get("use_refiner", False),
                },
            },
        }
        save_json(compiled.output_dir / "metadata.json", metadata)
        scene_clip_paths.append(clip_path)

    if compile_only:
        return

    # scene-level assembly + audio
    scene_video_no_audio = scene_out_dir / "scene_video_no_audio.mp4"
    concat_clips(scene_clip_paths, scene_video_no_audio)

    total_duration = float(sum(float(s.shot_data.get("duration", 0.0)) for s in compiled_shots))
    audio_dir = scene_out_dir / "audio"
    ensure_dir(audio_dir)

    dialog_signature = compute_signature(
        {
            "audio_hash": compiled_shots[0].audio_hash,
            "total_duration": total_duration,
            "code_git": get_git_hash(),
        }
    )

    dialog_track = audio_dir / "dialog_track.wav"
    music_track = audio_dir / "music_track.wav"
    final_audio = audio_dir / "final_audio.wav"

    should_render_audio = not should_skip(
        compiled_dir=compiled_shots[0].compiled_dir,
        task_key="scene_audio",
        signature=dialog_signature,
        required_outputs=[dialog_track, music_track, final_audio],
        resume=resume,
    )

    if should_render_audio:
        dialog_rendered = render_dialog_track(
            dialog_yaml=scene_dialog_data,
            project_root=project.path.parent,
            output_dir=audio_dir,
            total_duration_sec=total_duration,
            default_sample_rate=24000,
        )
        write_srt(scene_dialog_data, audio_dir / "subtitles.srt")

        music_override = scene_data.get("music_override")
        if music_override and _copy_if_exists(_resolve_path(ws_dir, str(music_override)), music_track):
            logger.info("Using music override track: %s", music_override)
        else:
            scene_prompt = str(scene_data.get("vibe_overrides", {}).get("prompt", ""))
            render_music_track(
                project_root=project.path.parent,
                scene_prompt=scene_prompt,
                duration_sec=total_duration,
                output_path=music_track,
                sample_rate=24000,
            )

        mix_dialog_and_music(
            dialog_path=dialog_rendered,
            music_path=music_track,
            output_path=final_audio,
            target_lufs=float(project.data.get("output_specs", {}).get("loudness_target_lufs", -16.0)),
            ducking_db=-8.0,
            fade_in_sec=0.3,
            fade_out_sec=0.5,
        )
        update_task_signature(compiled_shots[0].compiled_dir, "scene_audio", dialog_signature)
    else:
        logger.info("Skipping scene audio render (cache hit) for %s/%s", project.name, scene_name)

    scene_output = scene_out_dir / "scene.mp4"
    mux_audio(scene_video_no_audio, final_audio, scene_output)

    a_stats = audio_stats(final_audio) if final_audio.exists() else {"lufs": -30.0, "clipping_ratio": 0.0}
    for compiled in compiled_shots:
        meta_path = compiled.output_dir / "metadata.json"
        if meta_path.exists():
            meta = load_json(meta_path)
            meta["audio_stats"] = a_stats
            meta["loudness_target_lufs"] = float(project.data.get("output_specs", {}).get("loudness_target_lufs", -16.0))
            save_json(meta_path, meta)


def finalize_project_video(output_root: Path, run_id: str, project_name: str, scene_names: list[str]) -> Path:
    project_dir = output_root / run_id / project_name
    clips = [project_dir / scene / "scene.mp4" for scene in scene_names if (project_dir / scene / "scene.mp4").exists()]
    final_path = project_dir / "final.mp4"
    concat_clips(clips, final_path)
    return final_path
