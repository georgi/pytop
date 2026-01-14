"""pytop - Main Textual application."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Footer, Static

from pytop.models import ProcessSnapshot

# Mock data for Phase 1
MOCK_PROCESSES = [
    ProcessSnapshot(
        pid=1,
        name="systemd",
        username="root",
        status="S",
        cpu_percent=0.1,
        memory_percent=0.5,
        memory_rss=10485760,
        threads=1,
        nice=0,
        command_line="/sbin/init",
    ),
    ProcessSnapshot(
        pid=123,
        name="python",
        username="user",
        status="R",
        cpu_percent=25.3,
        memory_percent=2.1,
        memory_rss=52428800,
        threads=4,
        nice=0,
        command_line="python pytop/app.py",
    ),
    ProcessSnapshot(
        pid=456,
        name="bash",
        username="user",
        status="S",
        cpu_percent=0.0,
        memory_percent=0.3,
        memory_rss=5242880,
        threads=1,
        nice=0,
        command_line="/bin/bash",
    ),
    ProcessSnapshot(
        pid=789,
        name="nginx",
        username="www-data",
        status="S",
        cpu_percent=1.2,
        memory_percent=1.5,
        memory_rss=31457280,
        threads=8,
        nice=-5,
        command_line="nginx: worker process",
    ),
    ProcessSnapshot(
        pid=1024,
        name="postgres",
        username="postgres",
        status="S",
        cpu_percent=3.5,
        memory_percent=4.2,
        memory_rss=87031808,
        threads=12,
        nice=0,
        command_line="/usr/lib/postgresql/15/bin/postgres",
    ),
]


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "K", "M", "G", "T"]:
        if size < 1024:
            return f"{size:5.1f}{unit}" if unit != "B" else f"{size:5d}{unit}"
        size = size / 1024
    return f"{size:.1f}P"


class HeaderStats(Static):
    """Header widget showing CPU and memory statistics."""

    DEFAULT_CSS = """
    HeaderStats {
        height: auto;
        min-height: 5;
        padding: 1;
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the header stats layout."""
        yield Horizontal(
            Static(self._get_cpu_info(), id="cpu-info"),
            Static(self._get_mem_info(), id="mem-info"),
        )

    def _get_cpu_info(self) -> str:
        """Get mock CPU info display."""
        # Mock CPU bars for Phase 1
        lines = []
        for i in range(4):
            usage = [25.0, 50.0, 75.0, 10.0][i]
            bar_len = int(usage / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"CPU{i} [{bar}] {usage:5.1f}%")
        return "\n".join(lines)

    def _get_mem_info(self) -> str:
        """Get mock memory info display."""
        # Mock memory info for Phase 1
        return (
            "Mem[████████████░░░░░░░░] 8.0G/16.0G\n"
            "Swp[░░░░░░░░░░░░░░░░░░░░] 0.0G/4.0G\n"
            "Load average: 1.25 0.98 0.76\n"
            "Uptime: 5 days, 12:34:56"
        )


class ProcessTable(Container):
    """Container for the process data table."""

    DEFAULT_CSS = """
    ProcessTable {
        height: 1fr;
        border: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the process table."""
        yield DataTable(id="process-table")

    def on_mount(self) -> None:
        """Initialize the data table when mounted."""
        table = self.query_one("#process-table", DataTable)
        table.cursor_type = "row"

        # Add columns
        table.add_column("PID", key="pid", width=8)
        table.add_column("USER", key="user", width=10)
        table.add_column("NI", key="nice", width=4)
        table.add_column("S", key="status", width=3)
        table.add_column("CPU%", key="cpu", width=8)
        table.add_column("MEM%", key="mem", width=8)
        table.add_column("RES", key="rss", width=8)
        table.add_column("THR", key="threads", width=5)
        table.add_column("Command", key="command")

        # Add mock data rows
        for proc in MOCK_PROCESSES:
            table.add_row(
                str(proc.pid),
                proc.username[:10],
                str(proc.nice),
                proc.status,
                f"{proc.cpu_percent:5.1f}",
                f"{proc.memory_percent:5.1f}",
                format_bytes(proc.memory_rss),
                str(proc.threads),
                proc.command_line[:50],
                key=str(proc.pid),
            )


class PytopApp(App):
    """Main pytop application."""

    TITLE = "pytop"
    SUB_TITLE = "Python System Monitor"

    CSS = """
    Screen {
        layout: vertical;
    }

    #header-stats {
        dock: top;
        height: auto;
        min-height: 6;
    }

    Horizontal {
        height: auto;
    }

    #cpu-info {
        width: 1fr;
        padding-right: 2;
    }

    #mem-info {
        width: 1fr;
        padding-left: 2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("f6", "sort", "Sort"),
        ("slash", "search", "Search"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield HeaderStats(id="header-stats")
        yield ProcessTable()
        yield Footer()

    def action_sort(self) -> None:
        """Handle sort action (placeholder for Phase 3)."""
        self.notify("Sort: Coming in Phase 3")

    def action_search(self) -> None:
        """Handle search action (placeholder for Phase 3)."""
        self.notify("Search: Coming in Phase 3")


def main() -> None:
    """Entry point for pytop application."""
    app = PytopApp()
    app.run()


if __name__ == "__main__":
    main()
