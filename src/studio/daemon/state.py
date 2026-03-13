"""
Persistent state management for the MovieStudio daemon.
Handles thread-safe state storage and retrieval.
"""

import json
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class MovieStatus(str, Enum):
    """Movie generation status lifecycle."""
    IDEATION = "IDEATION"
    WRITING = "WRITING"
    PLANNING = "PLANNING"
    GENERATING = "GENERATING"
    CRITIQUING = "CRITIQUING"
    REVISING = "REVISING"
    POST_PRODUCTION = "POST_PRODUCTION"
    PUBLISHED = "PUBLISHED"


@dataclass
class MovieState:
    """Represents the state of a single movie production."""
    id: str
    title: str
    status: MovieStatus = MovieStatus.IDEATION
    progress_pct: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    prompt: str = ""
    error_log: List[str] = field(default_factory=list)
    duration_seconds: int = 0
    video_path: Optional[str] = None
    poster_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MovieState':
        """Create from dictionary."""
        data_copy = data.copy()
        if isinstance(data_copy.get('status'), str):
            data_copy['status'] = MovieStatus(data_copy['status'])
        return MovieState(**data_copy)


@dataclass
class DaemonState:
    """Represents the overall state of the daemon."""
    current_movies: List[MovieState] = field(default_factory=list)
    completed_movies: List[MovieState] = field(default_factory=list)
    prompt_queue: List[str] = field(default_factory=list)
    gpu_status: Dict[str, Any] = field(default_factory=dict)
    last_model_scan: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    daemon_started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'current_movies': [m.to_dict() for m in self.current_movies],
            'completed_movies': [m.to_dict() for m in self.completed_movies],
            'prompt_queue': self.prompt_queue,
            'gpu_status': self.gpu_status,
            'last_model_scan': self.last_model_scan,
            'metrics': self.metrics,
            'daemon_started_at': self.daemon_started_at,
            'last_updated': self.last_updated,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DaemonState':
        """Create from dictionary."""
        return DaemonState(
            current_movies=[MovieState.from_dict(m) for m in data.get('current_movies', [])],
            completed_movies=[MovieState.from_dict(m) for m in data.get('completed_movies', [])],
            prompt_queue=data.get('prompt_queue', []),
            gpu_status=data.get('gpu_status', {}),
            last_model_scan=data.get('last_model_scan'),
            metrics=data.get('metrics', {}),
            daemon_started_at=data.get('daemon_started_at', datetime.utcnow().isoformat()),
            last_updated=data.get('last_updated', datetime.utcnow().isoformat()),
        )


class PersistentState:
    """Thread-safe persistent state manager for the daemon."""

    def __init__(self, state_file: Path):
        """Initialize state manager.

        Args:
            state_file: Path to JSON file for state persistence
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._state = self._load()

    def _load(self) -> DaemonState:
        """Load state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return DaemonState.from_dict(data)
            except Exception as e:
                print(f"Warning: Failed to load state file: {e}")
        return DaemonState()

    def _save(self) -> None:
        """Save state to JSON file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self._state.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error: Failed to save state: {e}")

    def get_state(self) -> DaemonState:
        """Get current state (thread-safe)."""
        with self._lock:
            return self._state

    def add_movie(self, movie: MovieState) -> None:
        """Add a new movie to current_movies."""
        with self._lock:
            self._state.current_movies.append(movie)
            self._state.last_updated = datetime.utcnow().isoformat()
            self._save()

    def update_movie(self, movie_id: str, **kwargs) -> Optional[MovieState]:
        """Update a movie by ID with given kwargs."""
        with self._lock:
            for i, movie in enumerate(self._state.current_movies):
                if movie.id == movie_id:
                    # Update fields
                    for key, value in kwargs.items():
                        if hasattr(movie, key):
                            setattr(movie, key, value)
                    movie.updated_at = datetime.utcnow().isoformat()
                    self._state.last_updated = datetime.utcnow().isoformat()
                    self._save()
                    return movie
            return None

    def move_to_completed(self, movie_id: str) -> Optional[MovieState]:
        """Move a movie from current to completed."""
        with self._lock:
            movie = None
            for i, m in enumerate(self._state.current_movies):
                if m.id == movie_id:
                    movie = self._state.current_movies.pop(i)
                    break

            if movie:
                movie.status = MovieStatus.PUBLISHED
                movie.updated_at = datetime.utcnow().isoformat()
                self._state.completed_movies.append(movie)
                self._state.last_updated = datetime.utcnow().isoformat()
                self._save()
                return movie
            return None

    def get_movie(self, movie_id: str) -> Optional[MovieState]:
        """Get a movie by ID from either current or completed."""
        with self._lock:
            for movie in self._state.current_movies:
                if movie.id == movie_id:
                    return movie
            for movie in self._state.completed_movies:
                if movie.id == movie_id:
                    return movie
            return None

    def add_to_queue(self, prompt: str) -> None:
        """Add a prompt to the queue."""
        with self._lock:
            self._state.prompt_queue.append(prompt)
            self._state.last_updated = datetime.utcnow().isoformat()
            self._save()

    def pop_from_queue(self) -> Optional[str]:
        """Pop the first prompt from the queue."""
        with self._lock:
            if self._state.prompt_queue:
                prompt = self._state.prompt_queue.pop(0)
                self._state.last_updated = datetime.utcnow().isoformat()
                self._save()
                return prompt
            return None

    def update_gpu_status(self, gpu_info: Dict[str, Any]) -> None:
        """Update GPU status information."""
        with self._lock:
            self._state.gpu_status = gpu_info
            self._state.last_updated = datetime.utcnow().isoformat()
            self._save()

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update metrics."""
        with self._lock:
            self._state.metrics.update(metrics)
            self._state.last_updated = datetime.utcnow().isoformat()
            self._save()

    def update_model_scan(self) -> None:
        """Update last model scan timestamp."""
        with self._lock:
            self._state.last_model_scan = datetime.utcnow().isoformat()
            self._state.last_updated = datetime.utcnow().isoformat()
            self._save()
