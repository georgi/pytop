"""pytop - Main Textual application."""

from enum import Enum
from queue import Empty, Queue

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Footer, Static

from pytop.models import ProcessSnapshot
from pytop.monitor import SystemMonitor, SystemSnapshot


class SortKey(Enum):
    """Sort keys for the process table."""

    CPU = "cpu"
    MEM = "mem"
    PID = "pid"
    USER = "user"


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

    def __init__(self, *args, **kwargs) -> None:
        """Initialize HeaderStats."""
        super().__init__(*args, **kwargs)
        self._cpu_percents: list[float] = []
        self._memory_total: int = 0
        self._memory_used: int = 0
        self._memory_percent: float = 0.0
        self._swap_total: int = 0
        self._swap_used: int = 0
        self._swap_percent: float = 0.0
        self._load_avg: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._uptime_seconds: float = 0.0

    def compose(self) -> ComposeResult:
        """Compose the header stats layout."""
        yield Horizontal(
            Static(self._get_cpu_info(), id="cpu-info"),
            Static(self._get_mem_info(), id="mem-info"),
        )

    def update_stats(self, snapshot: SystemSnapshot) -> None:
        """Update the statistics from a system snapshot."""
        self._cpu_percents = snapshot.cpu_percent_per_core
        self._memory_total = snapshot.memory_total
        self._memory_used = snapshot.memory_used
        self._memory_percent = snapshot.memory_percent
        self._swap_total = snapshot.swap_total
        self._swap_used = snapshot.swap_used
        self._swap_percent = snapshot.swap_percent
        self._load_avg = snapshot.load_avg
        self._uptime_seconds = snapshot.uptime_seconds
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the display with current data."""
        try:
            cpu_info = self.query_one("#cpu-info", Static)
            mem_info = self.query_one("#mem-info", Static)
            cpu_info.update(self._get_cpu_info())
            mem_info.update(self._get_mem_info())
        except Exception:
            pass  # Widget not mounted yet

    def _get_cpu_info(self) -> str:
        """Get CPU info display."""
        if not self._cpu_percents:
            return "Loading CPU info..."
        lines = []
        for i, usage in enumerate(self._cpu_percents):
            bar_len = int(usage / 5)
            bar_len = min(bar_len, 20)  # Cap at 20 chars
            bar = "[green]█[/green]" * bar_len + "[dim]░[/dim]" * (20 - bar_len)
            # Use escaped brackets for the bar container
            lines.append(f"CPU{i:<2} \\[{bar}] {usage:5.1f}%")
        return "\n".join(lines)

    def _get_mem_info(self) -> str:
        """Get memory info display."""
        if self._memory_total == 0:
            return "Loading memory info..."

        # Memory bar
        mem_bar_len = int(self._memory_percent / 5)
        mem_bar_len = min(mem_bar_len, 20)
        mem_bar = "[cyan]█[/cyan]" * mem_bar_len + "[dim]░[/dim]" * (20 - mem_bar_len)
        mem_used_gb = self._memory_used / (1024**3)
        mem_total_gb = self._memory_total / (1024**3)

        # Swap bar
        swap_bar_len = int(self._swap_percent / 5) if self._swap_total > 0 else 0
        swap_bar_len = min(swap_bar_len, 20)
        swap_bar = "[yellow]█[/yellow]" * swap_bar_len + "[dim]░[/dim]" * (20 - swap_bar_len)
        swap_used_gb = self._swap_used / (1024**3)
        swap_total_gb = self._swap_total / (1024**3)

        # Load average
        load_avg = self._load_avg

        # Uptime formatting
        uptime = self._uptime_seconds
        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        if days > 0:
            uptime_str = f"{days} days, {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Use escaped brackets for the bar containers
        return (
            f"Mem\\[{mem_bar}] {mem_used_gb:.1f}G/{mem_total_gb:.1f}G\n"
            f"Swp\\[{swap_bar}] {swap_used_gb:.1f}G/{swap_total_gb:.1f}G\n"
            f"Load average: {load_avg[0]:.2f} {load_avg[1]:.2f} {load_avg[2]:.2f}\n"
            f"Uptime: {uptime_str}"
        )


class ProcessTable(Container):
    """Container for the process data table."""

    DEFAULT_CSS = """
    ProcessTable {
        height: 1fr;
        border: solid $primary;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize ProcessTable."""
        super().__init__(*args, **kwargs)
        self._current_pids: set[int] = set()
        self._sort_key: SortKey = SortKey.CPU
        self._sort_reverse: bool = True  # Default: descending for CPU

    @property
    def sort_key(self) -> SortKey:
        """Get current sort key."""
        return self._sort_key

    def cycle_sort(self) -> SortKey:
        """Cycle to the next sort key and return it."""
        keys = list(SortKey)
        current_index = keys.index(self._sort_key)
        next_index = (current_index + 1) % len(keys)
        self._sort_key = keys[next_index]
        # Set sort order based on key
        self._sort_reverse = self._sort_key in (SortKey.CPU, SortKey.MEM)
        return self._sort_key

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

    def update_processes(self, processes: list[ProcessSnapshot]) -> None:
        """
        Update the process table with new data.

        Uses update_cell for existing rows to avoid re-rendering the whole table.
        """
        table = self.query_one("#process-table", DataTable)

        # Sort processes based on current sort key
        sorted_processes = self._sort_processes(processes)

        # Get current PIDs from the new snapshot
        new_pids = {proc.pid for proc in sorted_processes}

        # Remove rows for processes that no longer exist
        pids_to_remove = self._current_pids - new_pids
        for pid in pids_to_remove:
            try:
                table.remove_row(str(pid))
            except Exception:
                pass  # Row may not exist

        # Update existing rows or add new rows
        for proc in sorted_processes:
            row_key = str(proc.pid)

            if proc.pid in self._current_pids:
                # Update existing row using update_cell (performance optimization)
                self._update_row(table, row_key, proc)
            else:
                # Add new row
                self._add_row(table, row_key, proc)

        self._current_pids = new_pids

    def _sort_processes(self, processes: list[ProcessSnapshot]) -> list[ProcessSnapshot]:
        """Sort processes based on the current sort key."""
        key_func = {
            SortKey.CPU: lambda p: p.cpu_percent,
            SortKey.MEM: lambda p: p.memory_percent,
            SortKey.PID: lambda p: p.pid,
            SortKey.USER: lambda p: p.username.lower(),
        }
        return sorted(processes, key=key_func[self._sort_key], reverse=self._sort_reverse)

    def _update_row(self, table: DataTable, row_key: str, proc: ProcessSnapshot) -> None:
        """Update an existing row using update_cell for performance."""
        try:
            table.update_cell(row_key, "pid", str(proc.pid))
            table.update_cell(row_key, "user", proc.username[:10])
            table.update_cell(row_key, "nice", str(proc.nice))
            table.update_cell(row_key, "status", proc.status)
            table.update_cell(row_key, "cpu", f"{proc.cpu_percent:5.1f}")
            table.update_cell(row_key, "mem", f"{proc.memory_percent:5.1f}")
            table.update_cell(row_key, "rss", format_bytes(proc.memory_rss))
            table.update_cell(row_key, "threads", str(proc.threads))
            table.update_cell(row_key, "command", proc.command_line[:50])
        except Exception:
            pass  # Row may have been removed

    def _add_row(self, table: DataTable, row_key: str, proc: ProcessSnapshot) -> None:
        """Add a new row to the table."""
        try:
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
                key=row_key,
            )
        except Exception:
            pass  # Row may already exist


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

    def __init__(self) -> None:
        """Initialize the PytopApp."""
        super().__init__()
        self._update_queue: Queue[SystemSnapshot] = Queue()
        self._monitor = SystemMonitor(self._update_queue, poll_rate=2.0)

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield HeaderStats(id="header-stats")
        yield ProcessTable()
        yield Footer()

    def on_mount(self) -> None:
        """Start the system monitor when the app is mounted."""
        self._monitor.start()
        # Set up a timer to poll the queue for updates
        self.set_interval(0.5, self._check_for_updates)

    def _check_for_updates(self) -> None:
        """Check the queue for system updates and refresh the UI."""
        try:
            # Get the latest snapshot (drain the queue to get most recent)
            snapshot = None
            while True:
                try:
                    snapshot = self._update_queue.get_nowait()
                except Empty:
                    break

            if snapshot is not None:
                self._update_ui(snapshot)
        except Exception:
            # Per spec "Permission Grace": app must never crash
            pass

    def _update_ui(self, snapshot: SystemSnapshot) -> None:
        """Update the UI with the new system snapshot."""
        # Update header stats
        try:
            header = self.query_one("#header-stats", HeaderStats)
            header.update_stats(snapshot)
        except Exception:
            # Per spec "Permission Grace": app must never crash
            pass

        # Update process table
        try:
            process_table = self.query_one(ProcessTable)
            process_table.update_processes(snapshot.processes)
        except Exception:
            # Per spec "Permission Grace": app must never crash
            pass

    def action_sort(self) -> None:
        """Handle sort action - cycle through sort keys."""
        try:
            process_table = self.query_one(ProcessTable)
            new_sort_key = process_table.cycle_sort()
            self.notify(f"Sort: {new_sort_key.value.upper()}")
        except Exception:
            pass

    def action_search(self) -> None:
        """Handle search action (placeholder for future implementation)."""
        self.notify("Search: Coming soon")

    def action_quit(self) -> None:
        """Handle quit action with graceful cleanup."""
        self._monitor.stop()
        self.exit()


def main() -> None:
    """Entry point for pytop application."""
    app = PytopApp()
    app.run()


if __name__ == "__main__":
    main()
