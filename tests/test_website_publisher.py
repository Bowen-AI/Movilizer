from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from studio.website.publisher import MovieData, MoviePublisher


def _movie() -> MovieData:
    return MovieData(
        id="m1",
        title="Demo",
        synopsis="Synopsis",
        genre="Demo",
        duration_seconds=5,
        rating=4.0,
        generated_at=datetime.now(timezone.utc).isoformat(),
        thumbnail_url="",
        video_url="",
        metadata={},
    )


def test_publish_movie_falls_back_to_mp4_url_when_hls_missing(tmp_path: Path, monkeypatch) -> None:
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake-video")
    publisher = MoviePublisher(website_dir=tmp_path / "site")

    def fake_hls(src: Path, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "stream.mp4").write_bytes(b"fallback")

    monkeypatch.setattr(publisher, "_generate_hls", fake_hls)
    monkeypatch.setattr(publisher, "_generate_trailer", lambda *_args, **_kwargs: None)

    ok = publisher.publish_movie(movie_data=_movie(), video_path=source_video)
    assert ok is True

    saved = publisher.get_movie("m1")
    assert saved is not None
    assert saved["video_url"].endswith("/hls/stream.mp4")


def test_publish_movie_prefers_hls_playlist_when_present(tmp_path: Path, monkeypatch) -> None:
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake-video")
    publisher = MoviePublisher(website_dir=tmp_path / "site")

    def fake_hls(src: Path, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "stream.m3u8").write_text("#EXTM3U\n", encoding="utf-8")

    monkeypatch.setattr(publisher, "_generate_hls", fake_hls)
    monkeypatch.setattr(publisher, "_generate_trailer", lambda *_args, **_kwargs: None)

    ok = publisher.publish_movie(movie_data=_movie(), video_path=source_video)
    assert ok is True

    saved = publisher.get_movie("m1")
    assert saved is not None
    assert saved["video_url"].endswith("/hls/stream.m3u8")
