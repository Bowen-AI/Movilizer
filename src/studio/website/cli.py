from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .publisher import MovieData, MoviePublisher


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Website publishing utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    pub = sub.add_parser("publish", help="Publish an MP4 movie into website media/database")
    pub.add_argument("--video", required=True, help="Path to source video file")
    pub.add_argument("--movie_id", required=True, help="Movie ID")
    pub.add_argument("--title", required=True, help="Movie title")
    pub.add_argument("--synopsis", default="AI-generated movie", help="Movie synopsis")
    pub.add_argument("--genre", default="Sci-Fi", help="Movie genre")
    pub.add_argument("--rating", type=float, default=4.5, help="Movie rating")
    pub.add_argument("--duration_seconds", type=int, default=120, help="Movie duration in seconds")
    pub.add_argument("--website_dir", default="website", help="Website root directory")

    ls = sub.add_parser("list", help="List published movies")
    ls.add_argument("--website_dir", default="website", help="Website root directory")
    ls.add_argument("--limit", type=int, default=20)

    return parser


def _cmd_publish(args: argparse.Namespace) -> int:
    video = Path(args.video)
    if not video.exists():
        raise SystemExit(f"Video not found: {video}")

    publisher = MoviePublisher(website_dir=Path(args.website_dir))
    movie = MovieData(
        id=args.movie_id,
        title=args.title,
        synopsis=args.synopsis,
        genre=args.genre,
        duration_seconds=args.duration_seconds,
        rating=args.rating,
        generated_at=_iso_now(),
        thumbnail_url="",
        video_url="",
        metadata={"source_video": str(video)},
    )

    ok = publisher.publish_movie(movie_data=movie, video_path=video)
    if not ok:
        return 1

    published = publisher.get_movie(args.movie_id)
    print(json.dumps(published, indent=2))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    publisher = MoviePublisher(website_dir=Path(args.website_dir))
    movies = publisher.list_movies(limit=args.limit)
    print(json.dumps(movies, indent=2))
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "publish":
        raise SystemExit(_cmd_publish(args))
    if args.command == "list":
        raise SystemExit(_cmd_list(args))

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
