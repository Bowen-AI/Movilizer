"""Continuous GPU monitoring with health tracking and rebalancing triggers."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from .discovery import GPUDiscovery, GPUInfo

logger = logging.getLogger(__name__)


@dataclass
class GPUMetrics:
    """Metrics snapshot for a single GPU."""

    gpu: GPUInfo
    timestamp: datetime
    vram_utilization_pct: float
    power_draw_w: Optional[float] = None
    temperature_c: Optional[float] = None

    @property
    def is_critical_temp(self) -> bool:
        """Check if temperature is critical (>= 85C)."""
        return self.temperature_c is not None and self.temperature_c >= 85.0

    @property
    def is_high_temp(self) -> bool:
        """Check if temperature is high (>= 75C)."""
        return self.temperature_c is not None and self.temperature_c >= 75.0

    @property
    def is_fully_utilized(self) -> bool:
        """Check if GPU is fully utilized (>= 90%)."""
        return self.vram_utilization_pct >= 90.0

    @property
    def is_idle(self) -> bool:
        """Check if GPU is idle (< 5%)."""
        return self.vram_utilization_pct < 5.0


@dataclass
class HealthReport:
    """Health status report for GPU cluster."""

    timestamp: datetime
    healthy_gpus: int
    total_gpus: int
    overheated_gpus: list[int] = field(default_factory=list)
    throttled_gpus: list[int] = field(default_factory=list)
    underutilized_gpus: list[int] = field(default_factory=list)
    overutilized_gpus: list[int] = field(default_factory=list)
    needs_rebalancing: bool = False
    summary: str = ""

    def __repr__(self) -> str:
        return (
            f"HealthReport(healthy={self.healthy_gpus}/{self.total_gpus}, "
            f"overheated={len(self.overheated_gpus)}, "
            f"throttled={len(self.throttled_gpus)}, "
            f"rebalance_needed={self.needs_rebalancing})"
        )


class MetricsBuffer:
    """Fixed-size circular buffer for metrics history."""

    def __init__(self, gpu_index: int, max_size: int = 120) -> None:
        """Initialize metrics buffer."""
        self.gpu_index = gpu_index
        self.max_size = max_size
        self.buffer: deque[GPUMetrics] = deque(maxlen=max_size)

    def add(self, metrics: GPUMetrics) -> None:
        """Add metrics snapshot."""
        self.buffer.append(metrics)

    def get_history(self) -> list[GPUMetrics]:
        """Get all metrics in history."""
        return list(self.buffer)

    def avg_vram_utilization_pct(self, last_n: int = 5) -> float:
        """Average VRAM utilization over last N samples."""
        if not self.buffer:
            return 0.0
        samples = list(self.buffer)[-last_n:]
        return sum(m.vram_utilization_pct for m in samples) / len(samples)

    def avg_temperature_c(self, last_n: int = 5) -> Optional[float]:
        """Average temperature over last N samples."""
        temps = [
            m.temperature_c
            for m in list(self.buffer)[-last_n:]
            if m.temperature_c is not None
        ]
        if not temps:
            return None
        return sum(temps) / len(temps)

    def max_temperature_c(self, last_n: int = 5) -> Optional[float]:
        """Maximum temperature over last N samples."""
        temps = [
            m.temperature_c
            for m in list(self.buffer)[-last_n:]
            if m.temperature_c is not None
        ]
        if not temps:
            return None
        return max(temps)


class GPUMonitor:
    """Continuous GPU monitoring thread with health tracking."""

    def __init__(
        self,
        poll_interval_sec: float = 5.0,
        history_size: int = 120,
    ) -> None:
        """
        Initialize GPU monitor.

        Args:
            poll_interval_sec: Polling interval in seconds
            history_size: Number of historical samples to keep per GPU
        """
        self.poll_interval_sec = poll_interval_sec
        self.history_size = history_size

        self._discovery = GPUDiscovery()
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # State
        self._gpus: list[GPUInfo] = []
        self._metrics_buffers: dict[int, MetricsBuffer] = {}
        self._last_health_report: Optional[HealthReport] = None
        self._last_check_time = datetime.now(timezone.utc)

        # Callbacks
        self._rebalance_callbacks: list[Callable[[HealthReport], None]] = []

    def start(self) -> None:
        """Start monitoring thread."""
        with self._lock:
            if self._running:
                logger.warning("Monitor already running")
                return

            self._running = True
            self._thread = threading.Thread(
                target=self._monitor_loop, daemon=False, name="GPUMonitor"
            )
            self._thread.start()
            logger.info(f"GPU monitor started (poll_interval={self.poll_interval_sec}s)")

    def stop(self, timeout_sec: float = 10.0) -> bool:
        """Stop monitoring thread."""
        with self._lock:
            if not self._running:
                logger.warning("Monitor not running")
                return True

            self._running = False

        if self._thread:
            self._thread.join(timeout=timeout_sec)
            if self._thread.is_alive():
                logger.error(f"Monitor thread did not stop after {timeout_sec}s")
                return False

        logger.info("GPU monitor stopped")
        return True

    def register_rebalance_callback(self, callback: Callable[[HealthReport], None]) -> None:
        """Register callback for rebalancing triggers."""
        with self._lock:
            self._rebalance_callbacks.append(callback)

    def get_gpus(self) -> list[GPUInfo]:
        """Get current GPU states."""
        with self._lock:
            return self._gpus.copy()

    def get_metrics(self, gpu_index: int) -> Optional[MetricsBuffer]:
        """Get metrics history for a GPU."""
        with self._lock:
            return self._metrics_buffers.get(gpu_index)

    def get_latest_health_report(self) -> Optional[HealthReport]:
        """Get latest health report."""
        with self._lock:
            return self._last_health_report

    def refresh(self) -> list[GPUInfo]:
        """Force immediate refresh of GPU state."""
        gpus = self._discovery.get_gpus()
        with self._lock:
            self._gpus = gpus
            if not self._metrics_buffers:
                for gpu in gpus:
                    self._metrics_buffers[gpu.index] = MetricsBuffer(
                        gpu.index, max_size=self.history_size
                    )
        return gpus

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        try:
            # Initial discovery
            self.refresh()

            while self._running:
                try:
                    # Poll GPU state
                    gpus = self._discovery.get_gpus()

                    with self._lock:
                        self._gpus = gpus

                        # Create metrics for each GPU
                        now = datetime.now(timezone.utc)
                        for gpu in gpus:
                            metrics = GPUMetrics(
                                gpu=gpu,
                                timestamp=now,
                                vram_utilization_pct=gpu.vram_utilization_pct,
                                power_draw_w=gpu.power_draw_w,
                                temperature_c=gpu.temperature_c,
                            )

                            if gpu.index not in self._metrics_buffers:
                                self._metrics_buffers[gpu.index] = MetricsBuffer(
                                    gpu.index, max_size=self.history_size
                                )

                            self._metrics_buffers[gpu.index].add(metrics)

                        # Check health
                        health_report = self._evaluate_health(gpus)
                        self._last_health_report = health_report
                        self._last_check_time = now

                        # Trigger rebalancing if needed
                        if health_report.needs_rebalancing:
                            for callback in self._rebalance_callbacks:
                                try:
                                    callback(health_report)
                                except Exception as e:
                                    logger.error(f"Rebalance callback error: {e}")

                    time.sleep(self.poll_interval_sec)

                except Exception as e:
                    logger.error(f"Monitor loop error: {e}", exc_info=True)
                    time.sleep(self.poll_interval_sec)

        except Exception as e:
            logger.error(f"Monitor fatal error: {e}", exc_info=True)
        finally:
            self._running = False

    def _evaluate_health(self, gpus: list[GPUInfo]) -> HealthReport:
        """Evaluate overall GPU cluster health."""
        report = HealthReport(
            timestamp=datetime.now(timezone.utc),
            healthy_gpus=len(gpus),
            total_gpus=len(gpus),
        )

        for gpu in gpus:
            metrics_buf = self._metrics_buffers.get(gpu.index)
            if not metrics_buf:
                continue

            # Check for thermal issues
            if metrics_buf.max_temperature_c() is not None:
                max_temp = metrics_buf.max_temperature_c()
                if max_temp >= 85.0:
                    report.overheated_gpus.append(gpu.index)
                    report.healthy_gpus -= 1
                elif max_temp >= 75.0:
                    report.throttled_gpus.append(gpu.index)

            # Check utilization patterns
            avg_util = metrics_buf.avg_vram_utilization_pct(last_n=10)
            if avg_util < 5.0:
                report.underutilized_gpus.append(gpu.index)
            elif avg_util >= 90.0:
                report.overutilized_gpus.append(gpu.index)

        # Trigger rebalancing if:
        # - Any GPU overheated
        # - Significant utilization skew (some idle, some overutilized)
        report.needs_rebalancing = bool(
            report.overheated_gpus
            or (report.underutilized_gpus and report.overutilized_gpus)
        )

        # Generate summary
        summaries = []
        if report.overheated_gpus:
            summaries.append(f"Overheated: GPUs {report.overheated_gpus}")
        if report.throttled_gpus:
            summaries.append(f"Thermal throttling: GPUs {report.throttled_gpus}")
        if report.underutilized_gpus:
            summaries.append(f"Underutilized: GPUs {report.underutilized_gpus}")
        if report.overutilized_gpus:
            summaries.append(f"Overutilized: GPUs {report.overutilized_gpus}")

        report.summary = ", ".join(summaries) if summaries else "All GPUs healthy"

        return report


class MonitoredGPUCluster:
    """GPU cluster with continuous monitoring."""

    def __init__(self, poll_interval_sec: float = 5.0) -> None:
        """Initialize monitored cluster."""
        self.monitor = GPUMonitor(poll_interval_sec=poll_interval_sec)

    def start(self) -> None:
        """Start cluster monitoring."""
        self.monitor.start()

    def stop(self) -> bool:
        """Stop cluster monitoring."""
        return self.monitor.stop()

    def get_gpus(self) -> list[GPUInfo]:
        """Get current GPU states."""
        return self.monitor.get_gpus()

    def get_metrics(self, gpu_index: int) -> Optional[MetricsBuffer]:
        """Get metrics history for a GPU."""
        return self.monitor.get_metrics(gpu_index)

    def get_health_report(self) -> Optional[HealthReport]:
        """Get latest health report."""
        return self.monitor.get_latest_health_report()

    def refresh(self) -> list[GPUInfo]:
        """Force immediate refresh."""
        return self.monitor.refresh()

    def register_rebalance_callback(self, callback: Callable[[HealthReport], None]) -> None:
        """Register rebalancing callback."""
        self.monitor.register_rebalance_callback(callback)

    def __enter__(self) -> MonitoredGPUCluster:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
