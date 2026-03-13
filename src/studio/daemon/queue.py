"""
Thread-safe priority task queue for the movie generation pipeline.
"""

import heapq
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(str, Enum):
    """Types of tasks in the generation pipeline."""
    GENERATE = "GENERATE"
    CRITIQUE = "CRITIQUE"
    REVISE = "REVISE"
    PUBLISH = "PUBLISH"
    DISCOVER_MODELS = "DISCOVER_MODELS"


class TaskPriority(int, Enum):
    """Task priority levels (lower number = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class PriorityTask:
    """Represents a task in the queue."""
    priority: TaskPriority
    task_type: TaskType
    payload: Dict[str, Any] = field(default_factory=dict)
    movie_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # For heapq comparison (priority queue)
    def __lt__(self, other: 'PriorityTask') -> bool:
        """Compare tasks by priority, then creation time."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, older tasks first (FIFO)
        return self.created_at < other.created_at

    def __eq__(self, other: 'PriorityTask') -> bool:
        """Check equality by task_id."""
        return isinstance(other, PriorityTask) and self.task_id == other.task_id

    def __hash__(self) -> int:
        """Hash by task_id."""
        return hash(self.task_id)


class TaskQueue:
    """Thread-safe priority task queue with preemption support."""

    def __init__(self):
        """Initialize the task queue."""
        self._queue: List[PriorityTask] = []
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._active_tasks: Dict[str, PriorityTask] = {}

    def enqueue(self, task: PriorityTask) -> str:
        """Add a task to the queue.

        Args:
            task: PriorityTask to add

        Returns:
            Task ID
        """
        with self._lock:
            heapq.heappush(self._queue, task)
            self._not_empty.notify()
            return task.task_id

    def dequeue(self, timeout: Optional[float] = None) -> Optional[PriorityTask]:
        """Remove and return the highest priority task.

        Args:
            timeout: Maximum time to wait for a task (None = wait forever)

        Returns:
            PriorityTask or None if timeout expires
        """
        with self._not_empty:
            # Wait for a task to be available
            while not self._queue:
                if not self._not_empty.wait(timeout=timeout):
                    return None

            task = heapq.heappop(self._queue)
            self._active_tasks[task.task_id] = task
            return task

    def mark_complete(self, task_id: str) -> bool:
        """Mark a task as complete.

        Args:
            task_id: ID of the task to mark complete

        Returns:
            True if task was active, False otherwise
        """
        with self._lock:
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
                return True
            return False

    def preempt_for_critique(self, movie_id: str) -> None:
        """Insert a high-priority critique task (triggered by another critique).

        Args:
            movie_id: ID of the movie to critique
        """
        critique_task = PriorityTask(
            priority=TaskPriority.HIGH,
            task_type=TaskType.CRITIQUE,
            movie_id=movie_id,
            payload={"triggered_by": "preemption"},
        )
        self.enqueue(critique_task)

    def discover_models_task(self) -> None:
        """Enqueue a model discovery task."""
        task = PriorityTask(
            priority=TaskPriority.LOW,
            task_type=TaskType.DISCOVER_MODELS,
            payload={},
        )
        self.enqueue(task)

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        with self._lock:
            return {
                'queue_size': len(self._queue),
                'active_tasks': len(self._active_tasks),
                'tasks': [
                    {
                        'task_id': t.task_id,
                        'task_type': t.task_type.value,
                        'priority': t.priority.name,
                        'movie_id': t.movie_id,
                    }
                    for t in sorted(self._queue)
                ],
            }

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of active tasks."""
        with self._lock:
            return [
                {
                    'task_id': t.task_id,
                    'task_type': t.task_type.value,
                    'priority': t.priority.name,
                    'movie_id': t.movie_id,
                    'created_at': t.created_at,
                }
                for t in self._active_tasks.values()
            ]

    def clear_queue(self) -> int:
        """Clear all pending tasks (not active ones).

        Returns:
            Number of tasks cleared
        """
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    def size(self) -> int:
        """Get current queue size."""
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return len(self._queue) == 0
