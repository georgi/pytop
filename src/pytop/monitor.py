"""System monitoring engine for pytop."""

import threading
import time
from collections import deque
from dataclasses import dataclass
from queue import Queue

import psutil

from pytop.models import ProcessSnapshot


@dataclass(slots=True)
class SystemSnapshot:
    """Snapshot of overall system state."""

    cpu_percent_per_core: list[float]
    memory_total: int
    memory_used: int
    memory_percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    load_avg: tuple[float, float, float]
    uptime_seconds: float
    processes: list[ProcessSnapshot]


class SystemMonitor:
    """
    System monitor that collects process and system data using psutil.

    Runs in a separate daemon thread and pushes updates to a thread-safe Queue.
    Handles AccessDenied and ZombieProcess errors gracefully.
    """

    def __init__(
        self,
        update_queue: Queue[SystemSnapshot],
        poll_rate: float = 2.0,
    ) -> None:
        """
        Initialize the SystemMonitor.

        Args:
            update_queue: Thread-safe queue to push updates to.
            poll_rate: How often to poll the system (in seconds). Default 2.0s.
        """
        self._queue = update_queue
        self._poll_rate = poll_rate
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cpu_history: deque[list[float]] = deque(maxlen=60)
        # Initialize CPU percent (first call returns 0.0)
        psutil.cpu_percent(percpu=True)

    @property
    def poll_rate(self) -> float:
        """Get the current poll rate."""
        return self._poll_rate

    @poll_rate.setter
    def poll_rate(self, value: float) -> None:
        """Set the poll rate."""
        self._poll_rate = max(0.1, value)  # Minimum 0.1 seconds

    @property
    def is_running(self) -> bool:
        """Check if the monitor thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the monitoring thread."""
        if self.is_running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="SystemMonitor",
        )
        self._thread.start()

    def stop(self, timeout: float | None = 5.0) -> None:
        """
        Stop the monitoring thread.

        Args:
            timeout: How long to wait for thread to stop (seconds).
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _poll_loop(self) -> None:
        """Main polling loop running in the background thread."""
        while not self._stop_event.is_set():
            try:
                snapshot = self._collect_snapshot()
                self._queue.put(snapshot)
            except Exception:
                # Silently handle any unexpected errors to keep the loop running
                pass

            # Wait for poll_rate seconds or until stop is requested
            self._stop_event.wait(timeout=self._poll_rate)

    def _collect_snapshot(self) -> SystemSnapshot:
        """Collect a snapshot of the current system state."""
        # Collect CPU percentages (non-blocking, uses previous call's data)
        cpu_percents = psutil.cpu_percent(percpu=True)
        self._cpu_history.append(cpu_percents)

        # Collect memory info
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Collect load average
        load_avg = psutil.getloadavg()

        # Collect uptime
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        # Collect process snapshots
        processes = self._collect_processes()

        return SystemSnapshot(
            cpu_percent_per_core=cpu_percents,
            memory_total=mem.total,
            memory_used=mem.used,
            memory_percent=mem.percent,
            swap_total=swap.total,
            swap_used=swap.used,
            swap_percent=swap.percent,
            load_avg=load_avg,
            uptime_seconds=uptime,
            processes=processes,
        )

    def _collect_processes(self) -> list[ProcessSnapshot]:
        """
        Collect snapshots of all running processes.

        Uses psutil.process_iter() with oneshot() context manager for efficiency.
        Handles AccessDenied and ZombieProcess errors gracefully.
        """
        processes: list[ProcessSnapshot] = []

        # Attributes to fetch in oneshot
        attrs = [
            "pid",
            "name",
            "username",
            "status",
            "cpu_percent",
            "memory_percent",
            "memory_info",
            "num_threads",
            "nice",
            "cmdline",
        ]

        for proc in psutil.process_iter(attrs=attrs):
            try:
                # Use oneshot() context manager for efficient attribute access
                with proc.oneshot():
                    info = proc.info

                    # Get command line, handling None/empty cases
                    cmdline = info.get("cmdline") or []
                    command_line = " ".join(cmdline) if cmdline else info.get("name", "")

                    # Get memory RSS, defaulting to 0 if unavailable
                    mem_info = info.get("memory_info")
                    memory_rss = mem_info.rss if mem_info else 0

                    # Create snapshot with safe defaults for None values
                    snapshot = ProcessSnapshot(
                        pid=info.get("pid", 0),
                        name=info.get("name") or "",
                        username=info.get("username") or "",
                        status=info.get("status") or "?",
                        cpu_percent=info.get("cpu_percent") or 0.0,
                        memory_percent=info.get("memory_percent") or 0.0,
                        memory_rss=memory_rss,
                        threads=info.get("num_threads") or 0,
                        nice=info.get("nice") or 0,
                        command_line=command_line,
                    )
                    processes.append(snapshot)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Handle processes that died mid-poll, access denied, or zombies
                # Silently skip these processes as per spec requirements
                continue

        return processes

    def get_cpu_history(self) -> list[list[float]]:
        """Get the CPU usage history for sparkline rendering."""
        return list(self._cpu_history)
