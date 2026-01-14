"""Data models for pytop."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ProcessSnapshot:
    """Immutable snapshot of a process state."""

    pid: int
    name: str
    username: str
    status: str  # 'R', 'S', 'Z', 'D', etc.
    cpu_percent: float  # 0.0 - 100.0 * core_count
    memory_percent: float
    memory_rss: int  # Bytes
    threads: int
    nice: int
    command_line: str
