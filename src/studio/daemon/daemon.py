"""
MovieStudioDaemon - The autonomous movie generation engine.
Manages the complete lifecycle of AI-generated movies.
"""

import os
import signal
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from studio.daemon.queue import PriorityTask, TaskPriority, TaskQueue, TaskType
from studio.daemon.scheduler import (
    INTERVAL_5MIN,
    INTERVAL_DAILY,
    INTERVAL_HOURLY,
    DaemonScheduler,
)
from studio.daemon.state import DaemonState, MovieState, MovieStatus, PersistentState


class MovieStudioDaemon:
    """The heart of the Movilizer system - autonomous movie generation daemon.

    This daemon:
    1. Discovers available GPU/models
    2. Loads persisted state
    3. Processes queued prompts into complete movies
    4. Manages the full movie lifecycle (ideation → publishing)
    5. Handles critiques and revisions
    6. Publishes finished movies to the website
    7. Collects analytics and improves over time
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the daemon.

        Args:
            config_path: Path to daemon configuration YAML file
        """
        self.config = self._load_config(config_path)
        self.state_file = Path(self.config['state_file'])
        self.state_manager = PersistentState(self.state_file)
        self.task_queue = TaskQueue()
        self.scheduler = DaemonScheduler()

        self._running = False
        self._main_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # Initialize subsystems (will be wired up on start)
        self.gpu_manager = None
        self.model_discovery = None
        self.story_generator = None
        self.critics = None
        self.video_generator = None
        self.publisher = None
        self.analytics = None

        # Metrics
        self.stats = {
            'movies_generated': 0,
            'movies_published': 0,
            'critiques_run': 0,
            'revisions_made': 0,
            'total_runtime_seconds': 0,
        }

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load daemon configuration."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / 'configs' / 'daemon' / 'default.yaml'

        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}

        # Default config if file not found
        return {
            'state_file': 'state/daemon_state.json',
            'max_concurrent_tasks': 2,
            'enable_auto_critique': True,
            'critique_interval_percent': 25,
            'enable_analytics_feedback': True,
            'health_check_interval_seconds': 300,
            'model_discovery_enabled': True,
        }

    def start(self) -> None:
        """Start the daemon and all subsystems."""
        if self._running:
            print("Daemon already running")
            return

        print("=" * 60)
        print("MovieStudioDaemon Starting")
        print("=" * 60)

        self._running = True
        self._shutdown_event.clear()

        # Initialize subsystems
        self._init_subsystems()

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Setup scheduler tasks
        self._setup_scheduler()

        # Start scheduler
        self.scheduler.start()

        # Start main daemon loop
        self._main_thread = threading.Thread(target=self._main_loop, daemon=False)
        self._main_thread.start()

        print("Daemon started successfully")

    def _init_subsystems(self) -> None:
        """Initialize all subsystems."""
        print("Initializing subsystems...")

        try:
            from studio.gpu.manager import GPUManager
            self.gpu_manager = GPUManager()
            gpu_info = self.gpu_manager.get_status()
            self.state_manager.update_gpu_status(gpu_info)
            print(f"GPU Manager initialized: {gpu_info}")
        except Exception as e:
            print(f"Warning: GPU Manager initialization failed: {e}")

        try:
            from studio.discovery.scheduler import ModelDiscoveryScheduler
            self.model_discovery = ModelDiscoveryScheduler()
            print("Model Discovery initialized")
        except Exception as e:
            print(f"Warning: Model Discovery initialization failed: {e}")

        try:
            from studio.story.generator import StoryGenerator
            self.story_generator = StoryGenerator()
            print("Story Generator initialized")
        except Exception as e:
            print(f"Warning: Story Generator initialization failed: {e}")

        try:
            from studio.critics.main import CriticEnsemble
            self.critics = CriticEnsemble()
            print("Critics initialized")
        except Exception as e:
            print(f"Warning: Critics initialization failed: {e}")

        try:
            from studio.models.generator import VideoGenerator
            self.video_generator = VideoGenerator()
            print("Video Generator initialized")
        except Exception as e:
            print(f"Warning: Video Generator initialization failed: {e}")

        try:
            from studio.website.publisher import MoviePublisher
            self.publisher = MoviePublisher()
            print("Movie Publisher initialized")
        except Exception as e:
            print(f"Warning: Movie Publisher initialization failed: {e}")

        try:
            from studio.website.analytics import AnalyticsProcessor
            self.analytics = AnalyticsProcessor()
            print("Analytics Processor initialized")
        except Exception as e:
            print(f"Warning: Analytics Processor initialization failed: {e}")

        state = self.state_manager.get_state()
        print(f"State loaded: {len(state.current_movies)} active, {len(state.completed_movies)} completed")

    def _setup_scheduler(self) -> None:
        """Setup periodic scheduler tasks."""
        # Model discovery (daily)
        if self.config.get('model_discovery_enabled', True):
            self.scheduler.add_task(
                'model_discovery',
                self._task_discover_models,
                INTERVAL_DAILY,
                start_immediately=True,
            )

        # Analytics processing (hourly)
        if self.config.get('enable_analytics_feedback', True):
            self.scheduler.add_task(
                'analytics_processing',
                self._task_process_analytics,
                INTERVAL_HOURLY,
                start_immediately=False,
            )

        # Health check (every 5 min)
        self.scheduler.add_task(
            'health_check',
            self._task_health_check,
            INTERVAL_5MIN,
            start_immediately=True,
        )

    def _main_loop(self) -> None:
        """Main daemon event loop."""
        print("Main loop starting...")
        loop_count = 0
        start_time = time.time()

        while self._running and not self._shutdown_event.is_set():
            loop_count += 1

            try:
                # Check for queued prompts
                if self.task_queue.is_empty():
                    self._check_for_prompts()

                # Process next task
                task = self.task_queue.dequeue(timeout=5)
                if task:
                    self._process_task(task)

                # Update metrics periodically
                if loop_count % 10 == 0:
                    elapsed = time.time() - start_time
                    self.stats['total_runtime_seconds'] = int(elapsed)
                    self.state_manager.update_metrics(self.stats)

            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

        elapsed = time.time() - start_time
        self.stats['total_runtime_seconds'] = int(elapsed)
        self.state_manager.update_metrics(self.stats)
        print(f"Main loop stopped after {loop_count} iterations ({elapsed:.1f}s)")

    def _check_for_prompts(self) -> None:
        """Check for and enqueue prompts from the queue."""
        prompt = self.state_manager.pop_from_queue()
        if prompt:
            movie_id = str(uuid.uuid4())
            movie = MovieState(
                id=movie_id,
                title=prompt[:50],
                status=MovieStatus.IDEATION,
                prompt=prompt,
            )
            self.state_manager.add_movie(movie)

            # Enqueue generation task
            task = PriorityTask(
                priority=TaskPriority.NORMAL,
                task_type=TaskType.GENERATE,
                movie_id=movie_id,
                payload={'prompt': prompt},
            )
            self.task_queue.enqueue(task)
            print(f"Enqueued movie generation: {movie_id}")

    def _process_task(self, task: PriorityTask) -> None:
        """Process a single task from the queue."""
        print(f"Processing task: {task.task_type.value} for movie {task.movie_id}")
        movie_id = task.movie_id

        try:
            if task.task_type == TaskType.GENERATE:
                self._execute_generate(task)
            elif task.task_type == TaskType.CRITIQUE:
                self._execute_critique(task)
            elif task.task_type == TaskType.REVISE:
                self._execute_revise(task)
            elif task.task_type == TaskType.PUBLISH:
                self._execute_publish(task)
            elif task.task_type == TaskType.DISCOVER_MODELS:
                self._execute_discover_models(task)

            self.task_queue.mark_complete(task.task_id)

        except Exception as e:
            print(f"Error processing task {task.task_id}: {e}")
            if movie_id:
                self.state_manager.update_movie(
                    movie_id,
                    error_log=[str(e)],
                )
            self.task_queue.mark_complete(task.task_id)

    def _execute_generate(self, task: PriorityTask) -> None:
        """Execute story generation and video generation."""
        movie_id = task.movie_id
        prompt = task.payload.get('prompt', '')

        self.state_manager.update_movie(movie_id, status=MovieStatus.WRITING)

        # Generate story (if we have a story generator)
        if self.story_generator:
            # This would call the actual story generator
            # For now, we simulate it
            print(f"Generating story for {movie_id}...")
            time.sleep(0.1)  # Simulate work
            story = f"Generated story for: {prompt}"

            self.state_manager.update_movie(
                movie_id,
                status=MovieStatus.PLANNING,
                progress_pct=25,
            )

        # Generate scenes/video (if we have a video generator)
        if self.video_generator:
            print(f"Generating video for {movie_id}...")
            time.sleep(0.1)  # Simulate work
            video_path = f"outputs/{movie_id}/video.mp4"
            poster_path = f"outputs/{movie_id}/poster.png"

            self.state_manager.update_movie(
                movie_id,
                status=MovieStatus.GENERATING,
                progress_pct=75,
                video_path=video_path,
                poster_path=poster_path,
            )

        # Update progress
        self.state_manager.update_movie(
            movie_id,
            status=MovieStatus.CRITIQUING,
            progress_pct=85,
        )

        # Enqueue critique task
        if self.config.get('enable_auto_critique', True):
            critique_task = PriorityTask(
                priority=TaskPriority.HIGH,
                task_type=TaskType.CRITIQUE,
                movie_id=movie_id,
                payload={},
            )
            self.task_queue.enqueue(critique_task)

        self.stats['movies_generated'] += 1

    def _execute_critique(self, task: PriorityTask) -> None:
        """Execute critic ensemble review."""
        movie_id = task.movie_id
        print(f"Running critique for {movie_id}...")

        movie = self.state_manager.get_movie(movie_id)
        if not movie:
            return

        self.state_manager.update_movie(movie_id, status=MovieStatus.CRITIQUING)

        # Run critics (if available)
        if self.critics:
            # This would call the actual critics
            # For now, simulate
            time.sleep(0.1)
            scores = {
                'narrative': 7.5,
                'visuals': 8.2,
                'audio': 7.8,
                'overall': 7.8,
            }
        else:
            scores = {'overall': 8.0}

        # Decide if revision needed
        needs_revision = scores.get('overall', 10) < 8.0

        if needs_revision and movie.metadata.get('revision_count', 0) < 3:
            # Enqueue revision
            revision_task = PriorityTask(
                priority=TaskPriority.HIGH,
                task_type=TaskType.REVISE,
                movie_id=movie_id,
                payload={'critique_scores': scores},
            )
            self.task_queue.enqueue(revision_task)
            self.state_manager.update_movie(
                movie_id,
                status=MovieStatus.REVISING,
                metadata={
                    **movie.metadata,
                    'revision_count': movie.metadata.get('revision_count', 0) + 1,
                    'last_scores': scores,
                },
            )
        else:
            # Enqueue publish
            publish_task = PriorityTask(
                priority=TaskPriority.NORMAL,
                task_type=TaskType.PUBLISH,
                movie_id=movie_id,
                payload={'final_scores': scores},
            )
            self.task_queue.enqueue(publish_task)
            self.state_manager.update_movie(
                movie_id,
                status=MovieStatus.POST_PRODUCTION,
                progress_pct=90,
                metadata={**movie.metadata, 'final_scores': scores},
            )

        self.stats['critiques_run'] += 1

    def _execute_revise(self, task: PriorityTask) -> None:
        """Execute revision based on critique feedback."""
        movie_id = task.movie_id
        print(f"Revising movie {movie_id}...")

        self.state_manager.update_movie(movie_id, status=MovieStatus.REVISING)

        # Simulate revision
        time.sleep(0.1)

        # Re-critique after revision
        critique_task = PriorityTask(
            priority=TaskPriority.NORMAL,
            task_type=TaskType.CRITIQUE,
            movie_id=movie_id,
            payload={},
        )
        self.task_queue.enqueue(critique_task)

        self.stats['revisions_made'] += 1

    def _execute_publish(self, task: PriorityTask) -> None:
        """Publish finished movie to website."""
        movie_id = task.movie_id
        print(f"Publishing movie {movie_id}...")

        movie = self.state_manager.get_movie(movie_id)
        if not movie or not movie.video_path:
            print(f"Cannot publish {movie_id}: missing video")
            return

        # Publish (if we have a publisher)
        if self.publisher:
            # This would call the actual publisher
            # For now, simulate
            time.sleep(0.1)

        # Move to completed
        self.state_manager.move_to_completed(movie_id)
        self.stats['movies_published'] += 1
        print(f"Published: {movie.title}")

    def _execute_discover_models(self, task: PriorityTask) -> None:
        """Discover available models and GPUs."""
        print("Discovering models...")
        if self.model_discovery:
            # This would call the actual discovery
            # For now, simulate
            time.sleep(0.1)
        self.state_manager.update_model_scan()

    def _task_discover_models(self) -> None:
        """Scheduled task for model discovery."""
        task = PriorityTask(
            priority=TaskPriority.LOW,
            task_type=TaskType.DISCOVER_MODELS,
            payload={},
        )
        self.task_queue.enqueue(task)

    def _task_process_analytics(self) -> None:
        """Scheduled task for analytics processing."""
        if self.analytics:
            # Process analytics and get feedback
            insights = self.analytics.process_events()
            suggestions = self.analytics.generate_insights()
            print(f"Analytics insights: {insights}")

    def _task_health_check(self) -> None:
        """Scheduled task for health checks."""
        state = self.state_manager.get_state()
        queue_status = self.task_queue.get_queue_status()

        health = {
            'running': self._running,
            'active_movies': len(state.current_movies),
            'completed_movies': len(state.completed_movies),
            'queue_size': queue_status['queue_size'],
            'active_tasks': queue_status['active_tasks'],
        }

        if health['queue_size'] > 10:
            print(f"Warning: Large queue size: {health['queue_size']}")

        # Update state
        self.state_manager.update_metrics(health)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the daemon."""
        if not self._running:
            return

        print("=" * 60)
        print("MovieStudioDaemon Shutting Down")
        print("=" * 60)

        self._running = False
        self._shutdown_event.set()

        # Stop scheduler
        self.scheduler.stop()

        # Wait for main thread
        if self._main_thread:
            self._main_thread.join(timeout=10)

        # Final metrics update
        state = self.state_manager.get_state()
        print(f"\nFinal Stats:")
        print(f"  Active movies: {len(state.current_movies)}")
        print(f"  Completed movies: {len(state.completed_movies)}")
        print(f"  Movies generated: {self.stats['movies_generated']}")
        print(f"  Movies published: {self.stats['movies_published']}")
        print(f"  Critiques run: {self.stats['critiques_run']}")
        print(f"  Total runtime: {self.stats['total_runtime_seconds']}s")
        print("=" * 60)

    def add_prompt(self, prompt: str) -> str:
        """Add a prompt to the generation queue.

        Args:
            prompt: The prompt to add

        Returns:
            Movie ID that will be created
        """
        self.state_manager.add_to_queue(prompt)
        movie_id = str(uuid.uuid4())
        print(f"Prompt queued: {prompt[:50]}... (Movie ID: {movie_id})")
        return movie_id

    def get_status(self) -> Dict[str, Any]:
        """Get daemon status."""
        state = self.state_manager.get_state()
        queue_status = self.task_queue.get_queue_status()

        return {
            'running': self._running,
            'uptime_seconds': self.stats['total_runtime_seconds'],
            'active_movies': len(state.current_movies),
            'completed_movies': len(state.completed_movies),
            'queue_size': queue_status['queue_size'],
            'active_tasks': queue_status['active_tasks'],
            'stats': self.stats,
            'scheduler': self.scheduler.get_status(),
        }
