from pathlib import Path

from studio.media import video


def test_frames_to_clip_writes_fallback_note_without_ffmpeg(tmp_path: Path, monkeypatch) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    output = tmp_path / "out" / "clip.mp4"

    monkeypatch.setattr(video, "has_ffmpeg", lambda: False)

    ok = video.frames_to_clip(frames_dir, fps=24, output_path=output)

    assert ok is False
    note = output.with_suffix(".txt")
    assert note.exists()
    assert "ffmpeg missing" in note.read_text(encoding="utf-8")


def test_concat_clips_no_inputs_returns_false(tmp_path: Path) -> None:
    output = tmp_path / "out" / "joined.mp4"
    ok = video.concat_clips([], output)
    assert ok is False


def test_concat_clips_writes_fallback_note_without_ffmpeg(tmp_path: Path, monkeypatch) -> None:
    clip = tmp_path / "a.mp4"
    clip.write_bytes(b"fake")
    output = tmp_path / "out" / "joined.mp4"

    monkeypatch.setattr(video, "has_ffmpeg", lambda: False)

    ok = video.concat_clips([clip], output)
    assert ok is False
    note = output.with_suffix(".txt")
    assert note.exists()


def test_mux_audio_requires_inputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(video, "has_ffmpeg", lambda: True)

    ok = video.mux_audio(
        tmp_path / "missing_video.mp4",
        tmp_path / "missing_audio.wav",
        tmp_path / "out.mp4",
    )

    assert ok is False
