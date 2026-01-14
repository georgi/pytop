"""Tests for the SystemMonitor class."""

from queue import Queue

from pytop.models import ProcessSnapshot
from pytop.monitor import SystemMonitor, SystemSnapshot


class TestSystemSnapshot:
    """Tests for SystemSnapshot dataclass."""

    def test_system_snapshot_creation(self):
        """Test SystemSnapshot can be created with all fields."""
        snapshot = SystemSnapshot(
            cpu_percent_per_core=[10.0, 20.0, 30.0, 40.0],
            memory_total=16 * 1024**3,
            memory_used=8 * 1024**3,
            memory_percent=50.0,
            swap_total=4 * 1024**3,
            swap_used=0,
            swap_percent=0.0,
            load_avg=(1.0, 0.5, 0.25),
            uptime_seconds=3600.0,
            processes=[],
        )
        assert snapshot.cpu_percent_per_core == [10.0, 20.0, 30.0, 40.0]
        assert snapshot.memory_percent == 50.0
        assert snapshot.load_avg == (1.0, 0.5, 0.25)

    def test_system_snapshot_uses_slots(self):
        """Test SystemSnapshot uses __slots__ for memory efficiency."""
        snapshot = SystemSnapshot(
            cpu_percent_per_core=[],
            memory_total=0,
            memory_used=0,
            memory_percent=0.0,
            swap_total=0,
            swap_used=0,
            swap_percent=0.0,
            load_avg=(0.0, 0.0, 0.0),
            uptime_seconds=0.0,
            processes=[],
        )
        # Slots-based dataclasses don't have __dict__
        assert not hasattr(snapshot, "__dict__")


class TestSystemMonitor:
    """Tests for SystemMonitor class."""

    def test_monitor_creation(self):
        """Test SystemMonitor can be instantiated."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue)

        assert monitor.poll_rate == 2.0
        assert not monitor.is_running

    def test_monitor_custom_poll_rate(self):
        """Test SystemMonitor with custom poll rate."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=1.0)

        assert monitor.poll_rate == 1.0

    def test_poll_rate_minimum(self):
        """Test poll rate has a minimum value."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue)

        monitor.poll_rate = 0.01  # Very small value
        assert monitor.poll_rate >= 0.1  # Should be clamped to minimum

    def test_monitor_start_stop(self):
        """Test SystemMonitor can be started and stopped."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.1)

        assert not monitor.is_running

        monitor.start()
        assert monitor.is_running

        monitor.stop()
        assert not monitor.is_running

    def test_monitor_start_idempotent(self):
        """Test starting an already running monitor is safe."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.1)

        monitor.start()
        thread1 = monitor._thread

        monitor.start()  # Should not create a new thread
        thread2 = monitor._thread

        assert thread1 is thread2
        monitor.stop()

    def test_monitor_collects_data(self):
        """Test SystemMonitor collects and queues data."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.1)

        monitor.start()

        # Wait for at least one snapshot
        try:
            snapshot = queue.get(timeout=2.0)
            assert isinstance(snapshot, SystemSnapshot)
            assert isinstance(snapshot.cpu_percent_per_core, list)
            assert isinstance(snapshot.processes, list)
            assert snapshot.memory_total > 0
        finally:
            monitor.stop()

    def test_monitor_collects_processes(self):
        """Test SystemMonitor collects process snapshots."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.1)

        monitor.start()

        try:
            snapshot = queue.get(timeout=2.0)

            # There should be at least some processes
            assert len(snapshot.processes) > 0

            # All processes should be ProcessSnapshot instances
            for proc in snapshot.processes:
                assert isinstance(proc, ProcessSnapshot)
                assert proc.pid > 0
                assert isinstance(proc.name, str)
        finally:
            monitor.stop()

    def test_monitor_graceful_error_handling(self):
        """Test monitor handles errors gracefully and continues running."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.1)

        monitor.start()

        try:
            # Get multiple snapshots to ensure loop continues
            snapshot1 = queue.get(timeout=2.0)
            snapshot2 = queue.get(timeout=2.0)

            assert snapshot1 is not None
            assert snapshot2 is not None
        finally:
            monitor.stop()

    def test_monitor_cpu_history(self):
        """Test CPU history is recorded."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.1)

        monitor.start()

        try:
            # Wait for a couple of snapshots
            queue.get(timeout=2.0)
            queue.get(timeout=2.0)

            history = monitor.get_cpu_history()
            assert isinstance(history, list)
            assert len(history) >= 1
        finally:
            monitor.stop()

    def test_collect_processes_returns_list(self):
        """Test _collect_processes returns a list of ProcessSnapshot."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue)

        processes = monitor._collect_processes()

        assert isinstance(processes, list)
        assert len(processes) > 0
        for proc in processes:
            assert isinstance(proc, ProcessSnapshot)

    def test_process_snapshot_has_required_fields(self):
        """Test collected ProcessSnapshots have all required fields."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue)

        processes = monitor._collect_processes()

        # Check first few processes have valid data
        for proc in processes[:5]:
            assert proc.pid > 0
            assert isinstance(proc.name, str)
            assert isinstance(proc.username, str)
            assert isinstance(proc.status, str)
            assert isinstance(proc.cpu_percent, float)
            assert isinstance(proc.memory_percent, float)
            assert isinstance(proc.memory_rss, int)
            assert isinstance(proc.threads, int)
            assert isinstance(proc.nice, int)
            assert isinstance(proc.command_line, str)

    def test_daemon_thread(self):
        """Test monitor thread is a daemon thread."""
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.1)

        monitor.start()

        try:
            assert monitor._thread is not None
            assert monitor._thread.daemon is True
            assert monitor._thread.name == "SystemMonitor"
        finally:
            monitor.stop()
