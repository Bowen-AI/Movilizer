"""
Autonomous movie generation daemon for Movilizer.
Manages the continuous generation, critique, and publishing of AI movies.
"""

from studio.daemon.daemon import MovieStudioDaemon
from studio.daemon.queue import PriorityTask, TaskPriority, TaskQueue, TaskType
from studio.daemon.scheduler import DaemonScheduler
from studio.daemon.state import (
    DaemonState,
    MovieState,
    MovieStatus,
    PersistentState,
)

__all__ = [
    'MovieStudioDaemon',
    'PersistentState',
    'DaemonState',
    'MovieState',
    'MovieStatus',
    'TaskQueue',
    'TaskType',
    'PriorityTask',
    'TaskPriority',
    'DaemonScheduler',
]
