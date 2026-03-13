"""
Movie Publisher - Handles publishing generated movies to the website.
Manages video conversion, poster generation, and database updates.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MovieData:
    """Structured movie data for publishing."""
    id: str
    title: str
    synopsis: str
    genre: str
    duration_seconds: int
    rating: float
    generated_at: str
    thumbnail_url: str
    video_url: str
    trailer_url: Optional[str] = None
    metadata: Dict[str, Any] = None


class MoviePublisher:
    """Publishes AI-generated movies to the website."""

    def __init__(self, website_dir: Path = None):
        """Initialize the publisher.

        Args:
            website_dir: Path to website directory
        """
        if website_dir is None:
            website_dir = Path(__file__).parent.parent.parent.parent / 'website'

        self.website_dir = Path(website_dir)
        self.media_dir = self.website_dir / 'public' / 'media'
        self.data_dir = self.website_dir / 'public' / 'data'
        self.movies_db_file = self.data_dir / 'movies.json'

        # Create directories
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize movies database if not exists
        if not self.movies_db_file.exists():
            self._init_movies_db()

    def _init_movies_db(self) -> None:
        """Initialize empty movies database."""
        db = {
            'movies': [],
            'last_updated': datetime.utcnow().isoformat(),
            'total_movies': 0,
        }
        with open(self.movies_db_file, 'w') as f:
            json.dump(db, f, indent=2)

    def publish_movie(
        self,
        movie_data: MovieData,
        video_path: Path,
        poster_path: Optional[Path] = None,
    ) -> bool:
        """Publish a movie to the website.

        Args:
            movie_data: MovieData object with metadata
            video_path: Path to source video file (MP4)
            poster_path: Path to poster image

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Publishing movie: {movie_data.title}")

            # Create movie directory
            movie_dir = self.media_dir / movie_data.id
            movie_dir.mkdir(parents=True, exist_ok=True)

            # Copy/convert video to HLS
            hls_dir = movie_dir / 'hls'
            hls_dir.mkdir(exist_ok=True)
            self._generate_hls(video_path, hls_dir)

            # Copy poster
            if poster_path and poster_path.exists():
                poster_dest = movie_dir / 'poster.jpg'
                shutil.copy2(poster_path, poster_dest)
                movie_data.thumbnail_url = f'/media/{movie_data.id}/poster.jpg'

            # Generate trailer (extract first 30 seconds)
            trailer_path = movie_dir / 'trailer.mp4'
            self._generate_trailer(video_path, trailer_path)
            if trailer_path.exists():
                movie_data.trailer_url = f'/media/{movie_data.id}/trailer.mp4'

            # Set video URL to HLS stream
            movie_data.video_url = f'/media/{movie_data.id}/hls/stream.m3u8'

            # Update movies database
            self._add_to_movies_db(movie_data)

            print(f"Successfully published: {movie_data.title}")
            return True

        except Exception as e:
            print(f"Error publishing movie: {e}")
            return False

    def _generate_hls(self, source_video: Path, output_dir: Path) -> None:
        """Convert video to HLS format using ffmpeg.

        Args:
            source_video: Path to source MP4 file
            output_dir: Directory to output HLS segments
        """
        try:
            # Check if ffmpeg is available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except Exception:
            print("Warning: ffmpeg not available, skipping HLS conversion")
            # Just copy the video as fallback
            shutil.copy2(source_video, output_dir / 'stream.mp4')
            return

        # Convert to HLS with ffmpeg
        playlist_file = output_dir / 'stream.m3u8'
        segment_pattern = str(output_dir / 'segment_%03d.ts')

        try:
            subprocess.run(
                [
                    'ffmpeg',
                    '-i', str(source_video),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-hls_time', '10',  # 10 second segments
                    '-hls_playlist_type', 'vod',
                    '-hls_segment_filename', segment_pattern,
                    str(playlist_file),
                ],
                check=True,
                capture_output=True,
            )
            print(f"Generated HLS stream: {playlist_file}")
        except subprocess.CalledProcessError as e:
            print(f"ffmpeg error: {e}")

    def _generate_trailer(self, source_video: Path, output_path: Path) -> None:
        """Generate a trailer by extracting the first 30 seconds.

        Args:
            source_video: Path to source video
            output_path: Path to save trailer
        """
        try:
            subprocess.run([
                'ffmpeg',
                '-i', str(source_video),
                '-t', '30',  # First 30 seconds
                '-c:v', 'copy',
                '-c:a', 'copy',
                str(output_path),
            ], check=True, capture_output=True)
            print(f"Generated trailer: {output_path}")
        except Exception as e:
            print(f"Warning: Could not generate trailer: {e}")

    def _add_to_movies_db(self, movie_data: MovieData) -> None:
        """Add movie to the movies database.

        Args:
            movie_data: MovieData to add
        """
        with open(self.movies_db_file, 'r') as f:
            db = json.load(f)

        # Check if movie already exists
        existing = next(
            (m for m in db['movies'] if m['id'] == movie_data.id),
            None
        )

        movie_record = {
            'id': movie_data.id,
            'title': movie_data.title,
            'synopsis': movie_data.synopsis,
            'genre': movie_data.genre,
            'duration_seconds': movie_data.duration_seconds,
            'rating': movie_data.rating,
            'generated_at': movie_data.generated_at,
            'thumbnail_url': movie_data.thumbnail_url,
            'video_url': movie_data.video_url,
            'trailer_url': movie_data.trailer_url,
            'published_at': datetime.utcnow().isoformat(),
            'metadata': movie_data.metadata or {},
        }

        if existing:
            # Update existing movie
            idx = db['movies'].index(existing)
            db['movies'][idx] = movie_record
        else:
            # Add new movie
            db['movies'].append(movie_record)
            db['total_movies'] += 1

        db['last_updated'] = datetime.utcnow().isoformat()

        # Sort by generated_at descending (newest first)
        db['movies'].sort(key=lambda x: x['generated_at'], reverse=True)

        with open(self.movies_db_file, 'w') as f:
            json.dump(db, f, indent=2)

        print(f"Updated movies database: {db['total_movies']} total movies")

    def get_movie(self, movie_id: str) -> Optional[Dict[str, Any]]:
        """Get a published movie by ID.

        Args:
            movie_id: ID of the movie

        Returns:
            Movie record or None if not found
        """
        with open(self.movies_db_file, 'r') as f:
            db = json.load(f)

        return next((m for m in db['movies'] if m['id'] == movie_id), None)

    def list_movies(self, limit: int = 50, offset: int = 0) -> list:
        """List all published movies.

        Args:
            limit: Maximum number of movies to return
            offset: Number of movies to skip

        Returns:
            List of movie records
        """
        with open(self.movies_db_file, 'r') as f:
            db = json.load(f)

        movies = db['movies'][offset:offset + limit]
        return movies

    def get_by_genre(self, genre: str) -> list:
        """Get all movies of a specific genre.

        Args:
            genre: Genre to filter by

        Returns:
            List of movie records
        """
        with open(self.movies_db_file, 'r') as f:
            db = json.load(f)

        return [m for m in db['movies'] if m['genre'].lower() == genre.lower()]

    def delete_movie(self, movie_id: str) -> bool:
        """Delete a published movie.

        Args:
            movie_id: ID of the movie to delete

        Returns:
            True if deleted, False if not found
        """
        # Remove from database
        with open(self.movies_db_file, 'r') as f:
            db = json.load(f)

        original_count = len(db['movies'])
        db['movies'] = [m for m in db['movies'] if m['id'] != movie_id]

        if len(db['movies']) < original_count:
            with open(self.movies_db_file, 'w') as f:
                json.dump(db, f, indent=2)

            # Remove media files
            movie_dir = self.media_dir / movie_id
            if movie_dir.exists():
                shutil.rmtree(movie_dir)

            return True

        return False
