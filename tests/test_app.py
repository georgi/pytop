"""Tests for pytop application."""

import pytest

from pytop.app import ProcessTable, PytopApp, SortKey, format_bytes
from pytop.models import ProcessSnapshot
from pytop.monitor import SystemSnapshot


def test_format_bytes_bytes():
    """Test format_bytes with byte values."""
    assert "B" in format_bytes(500)


def test_format_bytes_kilobytes():
    """Test format_bytes with kilobyte values."""
    result = format_bytes(2048)
    assert "K" in result


def test_format_bytes_megabytes():
    """Test format_bytes with megabyte values."""
    result = format_bytes(5242880)
    assert "M" in result


def test_format_bytes_gigabytes():
    """Test format_bytes with gigabyte values."""
    result = format_bytes(1073741824)
    assert "G" in result


class TestSortKey:
    """Tests for SortKey enum."""

    def test_sort_key_values(self):
        """Test SortKey enum has expected values."""
        assert SortKey.CPU.value == "cpu"
        assert SortKey.MEM.value == "mem"
        assert SortKey.PID.value == "pid"
        assert SortKey.USER.value == "user"

    def test_sort_key_members(self):
        """Test SortKey enum has all expected members."""
        keys = list(SortKey)
        assert len(keys) == 4
        assert SortKey.CPU in keys
        assert SortKey.MEM in keys
        assert SortKey.PID in keys
        assert SortKey.USER in keys


@pytest.mark.asyncio
async def test_app_creation():
    """Test PytopApp can be instantiated."""
    app = PytopApp()
    assert app.title == "pytop"
    assert app.sub_title == "Python System Monitor"


@pytest.mark.asyncio
async def test_app_has_monitor():
    """Test PytopApp has SystemMonitor initialized."""
    app = PytopApp()
    assert app._monitor is not None
    assert app._update_queue is not None


@pytest.mark.asyncio
async def test_app_compose():
    """Test PytopApp composes correctly."""
    app = PytopApp()
    async with app.run_test() as pilot:
        # Verify the app has the expected widgets
        assert pilot.app.query_one("#header-stats") is not None
        assert pilot.app.query_one("#process-table") is not None


@pytest.mark.asyncio
async def test_app_quit_binding():
    """Test that 'q' binding triggers quit."""
    app = PytopApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        # App should be exiting
        assert pilot.app._exit


@pytest.mark.asyncio
async def test_app_sort_binding():
    """Test that F6 binding cycles sort key."""
    app = PytopApp()
    async with app.run_test() as pilot:
        process_table = pilot.app.query_one(ProcessTable)
        initial_sort = process_table.sort_key

        await pilot.press("f6")

        # Sort key should have changed
        new_sort = process_table.sort_key
        assert new_sort != initial_sort


@pytest.mark.asyncio
async def test_process_table_cycle_sort():
    """Test ProcessTable sort key cycling."""
    app = PytopApp()
    async with app.run_test() as pilot:
        process_table = pilot.app.query_one(ProcessTable)

        # Default should be CPU
        assert process_table.sort_key == SortKey.CPU

        # Cycle through all sort keys
        process_table.cycle_sort()
        assert process_table.sort_key == SortKey.MEM

        process_table.cycle_sort()
        assert process_table.sort_key == SortKey.PID

        process_table.cycle_sort()
        assert process_table.sort_key == SortKey.USER

        # Should wrap back to CPU
        process_table.cycle_sort()
        assert process_table.sort_key == SortKey.CPU


@pytest.mark.asyncio
async def test_process_table_update_processes():
    """Test ProcessTable updates with new process data."""
    app = PytopApp()
    async with app.run_test() as pilot:
        process_table = pilot.app.query_one(ProcessTable)

        # Create test processes
        test_processes = [
            ProcessSnapshot(
                pid=100,
                name="test1",
                username="user",
                status="R",
                cpu_percent=10.0,
                memory_percent=5.0,
                memory_rss=1024000,
                threads=1,
                nice=0,
                command_line="/bin/test1",
            ),
            ProcessSnapshot(
                pid=200,
                name="test2",
                username="root",
                status="S",
                cpu_percent=20.0,
                memory_percent=10.0,
                memory_rss=2048000,
                threads=2,
                nice=-5,
                command_line="/bin/test2",
            ),
        ]

        # Update the table
        process_table.update_processes(test_processes)

        # Check that PIDs are tracked
        assert 100 in process_table._current_pids
        assert 200 in process_table._current_pids


@pytest.mark.asyncio
async def test_process_table_removes_old_processes():
    """Test ProcessTable removes processes that no longer exist."""
    app = PytopApp()
    async with app.run_test() as pilot:
        process_table = pilot.app.query_one(ProcessTable)

        # Add initial processes
        initial_processes = [
            ProcessSnapshot(
                pid=100,
                name="test1",
                username="user",
                status="R",
                cpu_percent=10.0,
                memory_percent=5.0,
                memory_rss=1024000,
                threads=1,
                nice=0,
                command_line="/bin/test1",
            ),
            ProcessSnapshot(
                pid=200,
                name="test2",
                username="root",
                status="S",
                cpu_percent=20.0,
                memory_percent=10.0,
                memory_rss=2048000,
                threads=2,
                nice=-5,
                command_line="/bin/test2",
            ),
        ]
        process_table.update_processes(initial_processes)

        # Update with only one process
        new_processes = [
            ProcessSnapshot(
                pid=200,
                name="test2",
                username="root",
                status="S",
                cpu_percent=25.0,
                memory_percent=12.0,
                memory_rss=2048000,
                threads=2,
                nice=-5,
                command_line="/bin/test2",
            ),
        ]
        process_table.update_processes(new_processes)

        # PID 100 should be removed, PID 200 should remain
        assert 100 not in process_table._current_pids
        assert 200 in process_table._current_pids


@pytest.mark.asyncio
async def test_app_receives_updates_from_monitor():
    """Test that app receives updates from the system monitor."""
    app = PytopApp()
    async with app.run_test() as pilot:
        # Wait for at least one update cycle
        await pilot.pause(3)

        # Monitor should be running
        assert app._monitor.is_running

        # Process table should have data (from real system)
        process_table = pilot.app.query_one(ProcessTable)
        # After waiting, we should have received some processes
        assert len(process_table._current_pids) > 0


@pytest.mark.asyncio
async def test_header_stats_update():
    """Test that header stats can be updated."""
    app = PytopApp()
    async with app.run_test() as pilot:
        from pytop.app import HeaderStats

        header = pilot.app.query_one("#header-stats", HeaderStats)

        # Create a test snapshot
        test_snapshot = SystemSnapshot(
            cpu_percent_per_core=[10.0, 20.0],
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

        # Update stats
        header.update_stats(test_snapshot)

        # Verify stats were updated
        assert header._cpu_percents == [10.0, 20.0]
        assert header._memory_percent == 50.0
        assert header._load_avg == (1.0, 0.5, 0.25)
