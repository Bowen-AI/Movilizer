from pathlib import Path

from studio.tools.generate_sample_video import generate_sample_video


def test_generate_sample_video_creates_mp4(tmp_path: Path) -> None:
    output = tmp_path / "sample.mp4"
    generated = generate_sample_video(output=output, fps=8, seconds=0.5, width=160, height=120)

    assert generated == output
    assert output.exists()
    assert output.stat().st_size > 0
