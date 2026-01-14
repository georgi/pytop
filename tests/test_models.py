"""Tests for pytop data models."""

from pytop.models import ProcessSnapshot


def test_process_snapshot_creation():
    """Test ProcessSnapshot dataclass creation."""
    snapshot = ProcessSnapshot(
        pid=123,
        name="test_process",
        username="testuser",
        status="R",
        cpu_percent=50.0,
        memory_percent=25.0,
        memory_rss=1024000,
        threads=4,
        nice=0,
        command_line="/usr/bin/test",
    )

    assert snapshot.pid == 123
    assert snapshot.name == "test_process"
    assert snapshot.username == "testuser"
    assert snapshot.status == "R"
    assert snapshot.cpu_percent == 50.0
    assert snapshot.memory_percent == 25.0
    assert snapshot.memory_rss == 1024000
    assert snapshot.threads == 4
    assert snapshot.nice == 0
    assert snapshot.command_line == "/usr/bin/test"


def test_process_snapshot_is_frozen():
    """Test that ProcessSnapshot is immutable (frozen)."""
    snapshot = ProcessSnapshot(
        pid=1,
        name="init",
        username="root",
        status="S",
        cpu_percent=0.1,
        memory_percent=0.5,
        memory_rss=10000,
        threads=1,
        nice=0,
        command_line="/sbin/init",
    )

    # Attempting to modify should raise an error
    try:
        snapshot.pid = 999
        raise AssertionError("Should have raised FrozenInstanceError")
    except AttributeError:
        pass  # Expected behavior for frozen dataclass


def test_process_snapshot_uses_slots():
    """Test that ProcessSnapshot uses __slots__ for memory efficiency."""
    snapshot = ProcessSnapshot(
        pid=1,
        name="init",
        username="root",
        status="S",
        cpu_percent=0.1,
        memory_percent=0.5,
        memory_rss=10000,
        threads=1,
        nice=0,
        command_line="/sbin/init",
    )

    # Slots-based dataclasses don't have __dict__
    assert not hasattr(snapshot, "__dict__")
