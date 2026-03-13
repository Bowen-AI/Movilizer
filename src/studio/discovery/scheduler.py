"""Scheduler for managing model discovery and benchmarking."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..utils import get_logger, load_yaml, now_utc_iso, save_json, save_yaml

logger = get_logger("discovery.scheduler")


@dataclass
class ScheduleState:
    """State of the discovery scheduler."""

    enabled: bool = True
    last_scan_timestamp: str = ""
    last_benchmark_timestamp: str = ""
    scan_interval_hours: int = 24
    benchmark_interval_hours: int = 168  # 1 week
    active_task: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def should_run_scan(self) -> bool:
        """Check if it's time to run a scan."""
        if not self.last_scan_timestamp:
            return True

        try:
            last = datetime.fromisoformat(self.last_scan_timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours_since = (now - last).total_seconds() / 3600
            return hours_since >= self.scan_interval_hours
        except Exception:
            return True

    def should_run_benchmark(self) -> bool:
        """Check if it's time to run benchmarks."""
        if not self.last_benchmark_timestamp:
            return True

        try:
            last = datetime.fromisoformat(
                self.last_benchmark_timestamp.replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            hours_since = (now - last).total_seconds() / 3600
            return hours_since >= self.benchmark_interval_hours
        except Exception:
            return True


class DiscoveryScheduler:
    """Manages periodic model discovery and benchmarking."""

    def __init__(
        self,
        config: dict[str, Any],
        state_file: Path | str | None = None,
    ):
        """Initialize scheduler.

        Args:
            config: Discovery configuration dict.
            state_file: Path to persistence file for scheduler state.
        """
        self.config = config
        self.state_file = Path(state_file) if state_file else None
        self.state = self._load_state()
        self._timer: threading.Timer | None = None
        self._scan_callback: Callable | None = None
        self._benchmark_callback: Callable | None = None
        self._lock = threading.Lock()

    def _load_state(self) -> ScheduleState:
        """Load scheduler state from file."""
        if not self.state_file or not self.state_file.exists():
            return ScheduleState(
                scan_interval_hours=self.config.get("scan_interval_hours", 24),
                benchmark_interval_hours=self.config.get(
                    "benchmark_interval_hours", 168
                ),
            )

        try:
            data = load_yaml(self.state_file)
            return ScheduleState(
                enabled=data.get("enabled", True),
                last_scan_timestamp=data.get("last_scan_timestamp", ""),
                last_benchmark_timestamp=data.get("last_benchmark_timestamp", ""),
                scan_interval_hours=data.get(
                    "scan_interval_hours",
                    self.config.get("scan_interval_hours", 24),
                ),
                benchmark_interval_hours=data.get(
                    "benchmark_interval_hours",
                    self.config.get("benchmark_interval_hours", 168),
                ),
                active_task=data.get("active_task", ""),
                error_message=data.get("error_message", ""),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Failed to load scheduler state: {e}")
            return ScheduleState(
                scan_interval_hours=self.config.get("scan_interval_hours", 24),
                benchmark_interval_hours=self.config.get(
                    "benchmark_interval_hours", 168
                ),
            )

    def _save_state(self) -> None:
        """Save scheduler state to file."""
        if not self.state_file:
            return

        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "enabled": self.state.enabled,
                "last_scan_timestamp": self.state.last_scan_timestamp,
                "last_benchmark_timestamp": self.state.last_benchmark_timestamp,
                "scan_interval_hours": self.state.scan_interval_hours,
                "benchmark_interval_hours": self.state.benchmark_interval_hours,
                "active_task": self.state.active_task,
                "error_message": self.state.error_message,
                "metadata": self.state.metadata,
            }
            save_yaml(self.state_file, data)
            logger.debug(f"Saved scheduler state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")

    def register_scan_callback(self, callback: Callable) -> None:
        """Register callback for scan operations.

        Args:
            callback: Async or sync function to call for scans.
        """
        self._scan_callback = callback

    def register_benchmark_callback(self, callback: Callable) -> None:
        """Register callback for benchmark operations.

        Args:
            callback: Async or sync function to call for benchmarks.
        """
        self._benchmark_callback = callback

    def _run_scheduled_tasks(self) -> None:
        """Run scheduled tasks if intervals have elapsed."""
        with self._lock:
            if not self.state.enabled:
                logger.debug("Scheduler is disabled")
                return

            # Check and run scan
            if self.state.should_run_scan() and self._scan_callback:
                try:
                    logger.info("Running scheduled scan...")
                    self.state.active_task = "scanning"
                    self._scan_callback()
                    self.state.last_scan_timestamp = now_utc_iso()
                    self.state.error_message = ""
                except Exception as e:
                    logger.error(f"Scheduled scan failed: {e}")
                    self.state.error_message = str(e)
                finally:
                    self.state.active_task = ""

            # Check and run benchmark
            if self.state.should_run_benchmark() and self._benchmark_callback:
                try:
                    logger.info("Running scheduled benchmarks...")
                    self.state.active_task = "benchmarking"
                    self._benchmark_callback()
                    self.state.last_benchmark_timestamp = now_utc_iso()
                    self.state.error_message = ""
                except Exception as e:
                    logger.error(f"Scheduled benchmark failed: {e}")
                    self.state.error_message = str(e)
                finally:
                    self.state.active_task = ""

            # Save state
            self._save_state()

    def _schedule_next_run(self, interval_seconds: int = 3600) -> None:
        """Schedule next run of periodic tasks.

        Args:
            interval_seconds: Interval between checks in seconds.
        """
        self._timer = threading.Timer(interval_seconds, self._periodic_tick)
        self._timer.daemon = True
        self._timer.start()

    def _periodic_tick(self) -> None:
        """Periodic callback for running scheduled tasks."""
        try:
            self._run_scheduled_tasks()
        except Exception as e:
            logger.error(f"Error in periodic tick: {e}")
        finally:
            # Schedule next tick
            check_interval = self.config.get("check_interval_seconds", 3600)
            self._schedule_next_run(check_interval)

    def start(self) -> None:
        """Start the scheduler."""
        with self._lock:
            if self.state.enabled and not self._timer:
                logger.info("Starting discovery scheduler...")
                self.state.enabled = True
                check_interval = self.config.get("check_interval_seconds", 3600)
                self._schedule_next_run(check_interval)
                self._save_state()

    def stop(self) -> None:
        """Stop the scheduler."""
        with self._lock:
            if self._timer:
                logger.info("Stopping discovery scheduler...")
                self._timer.cancel()
                self._timer = None
            self.state.enabled = False
            self._save_state()

    def trigger_scan(self) -> None:
        """Manually trigger a scan."""
        with self._lock:
            if self._scan_callback:
                logger.info("Manually triggering scan...")
                try:
                    self.state.active_task = "scanning"
                    self._scan_callback()
                    self.state.last_scan_timestamp = now_utc_iso()
                    self.state.error_message = ""
                except Exception as e:
                    logger.error(f"Manual scan failed: {e}")
                    self.state.error_message = str(e)
                finally:
                    self.state.active_task = ""
                    self._save_state()

    def trigger_benchmark(self) -> None:
        """Manually trigger benchmarking."""
        with self._lock:
            if self._benchmark_callback:
                logger.info("Manually triggering benchmarks...")
                try:
                    self.state.active_task = "benchmarking"
                    self._benchmark_callback()
                    self.state.last_benchmark_timestamp = now_utc_iso()
                    self.state.error_message = ""
                except Exception as e:
                    logger.error(f"Manual benchmark failed: {e}")
                    self.state.error_message = str(e)
                finally:
                    self.state.active_task = ""
                    self._save_state()

    def set_scan_interval(self, hours: int) -> None:
        """Update scan interval.

        Args:
            hours: Interval in hours.
        """
        with self._lock:
            self.state.scan_interval_hours = max(1, hours)
            self._save_state()
            logger.info(f"Updated scan interval to {hours} hours")

    def set_benchmark_interval(self, hours: int) -> None:
        """Update benchmark interval.

        Args:
            hours: Interval in hours.
        """
        with self._lock:
            self.state.benchmark_interval_hours = max(1, hours)
            self._save_state()
            logger.info(f"Updated benchmark interval to {hours} hours")

    def get_status(self) -> dict[str, Any]:
        """Get current scheduler status.

        Returns:
            Status dict with timing and state information.
        """
        with self._lock:
            return {
                "enabled": self.state.enabled,
                "active_task": self.state.active_task,
                "last_scan": self.state.last_scan_timestamp,
                "last_benchmark": self.state.last_benchmark_timestamp,
                "scan_interval_hours": self.state.scan_interval_hours,
                "benchmark_interval_hours": self.state.benchmark_interval_hours,
                "should_scan": self.state.should_run_scan(),
                "should_benchmark": self.state.should_run_benchmark(),
                "error": self.state.error_message,
            }

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.stop()
