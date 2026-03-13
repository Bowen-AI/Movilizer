"""
Scheduler for periodic daemon tasks.
Manages recurring operations like model discovery, analytics, health checks.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        name: str,
        func: Callable,
        interval_seconds: float,
        start_immediately: bool = False,
    ):
        """Initialize a scheduled task.

        Args:
            name: Name of the task
            func: Callable to execute
            interval_seconds: How often to run (seconds)
            start_immediately: If True, run immediately on first schedule
        """
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.start_immediately = start_immediately
        self.last_run: Optional[datetime] = None
        self.next_run: datetime = (
            datetime.utcnow()
            if start_immediately
            else datetime.utcnow() + timedelta(seconds=interval_seconds)
        )
        self.run_count = 0
        self.error_count = 0
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.RLock()

    def should_run(self) -> bool:
        """Check if task should run now."""
        with self._lock:
            return datetime.utcnow() >= self.next_run

    def execute(self) -> bool:
        """Execute the task.

        Returns:
            True if successful, False if error
        """
        try:
            with self._lock:
                self.func()
                self.last_run = datetime.utcnow()
                self.next_run = datetime.utcnow() + timedelta(
                    seconds=self.interval_seconds
                )
                self.run_count += 1
            return True
        except Exception as e:
            with self._lock:
                self.error_count += 1
            print(f"Error in scheduled task '{self.name}': {e}")
            return False

    def get_status(self) -> Dict[str, any]:
        """Get task status."""
        with self._lock:
            return {
                'name': self.name,
                'interval_seconds': self.interval_seconds,
                'last_run': self.last_run.isoformat() if self.last_run else None,
                'next_run': self.next_run.isoformat(),
                'run_count': self.run_count,
                'error_count': self.error_count,
            }


class DaemonScheduler:
    """Manages scheduled tasks for the daemon."""

    def __init__(self):
        """Initialize the scheduler."""
        self.tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: float,
        start_immediately: bool = False,
    ) -> None:
        """Add a task to be scheduled.

        Args:
            name: Name of the task
            func: Callable to execute
            interval_seconds: How often to run (seconds)
            start_immediately: If True, run immediately on first schedule
        """
        with self._lock:
            if name in self.tasks:
                raise ValueError(f"Task '{name}' already exists")
            self.tasks[name] = ScheduledTask(
                name, func, interval_seconds, start_immediately
            )

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"Scheduler started with {len(self.tasks)} tasks")

    def stop(self) -> None:
        """Stop the scheduler."""
        with self._lock:
            self._running = False

        if self._thread:
            self._thread.join(timeout=5)
        print("Scheduler stopped")

    def _run(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                with self._lock:
                    tasks_to_run = [
                        task
                        for task in self.tasks.values()
                        if task.should_run()
                    ]

                for task in tasks_to_run:
                    if self._running:
                        task.execute()

                # Check again in 1 second
                time.sleep(1)
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                time.sleep(1)

    def get_status(self) -> Dict[str, any]:
        """Get status of all tasks."""
        with self._lock:
            return {
                'running': self._running,
                'task_count': len(self.tasks),
                'tasks': [task.get_status() for task in self.tasks.values()],
            }

    def get_task_status(self, task_name: str) -> Optional[Dict[str, any]]:
        """Get status of a specific task."""
        with self._lock:
            task = self.tasks.get(task_name)
            return task.get_status() if task else None


# Common interval constants (in seconds)
INTERVAL_5MIN = 5 * 60
INTERVAL_HOURLY = 60 * 60
INTERVAL_DAILY = 24 * 60 * 60
