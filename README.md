# pytop

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/pytop.svg)](https://pypi.org/project/pytop/)

A Python system monitor (htop clone) built with Textual and psutil. Features real-time CPU, memory, and process monitoring in a terminal UI.

## Features

- Real-time per-core CPU usage visualization
- Memory and swap usage with progress bars
- Load average and system uptime display
- Process table with sorting (CPU, MEM, PID, USER)
- Keyboard navigation
- Zero-lag UI via threaded architecture
- Graceful error handling for permission issues

## Requirements

- Python 3.12+
- psutil >= 6.0
- textual >= 0.50.0

## Installation

```bash
pip install -e .
```

## Usage

```bash
pytop
```

![pytop system monitor](screenshot.png)

## Keybindings

| Key | Action |
|-----|--------|
| `q` / `F10` | Quit |
| `F6` / `>` | Cycle sort column |
| `/` | Search (coming soon) |

## Architecture

- **SystemMonitor**: Daemon thread polling system data via psutil
- **PytopApp**: Textual TUI receiving updates via thread-safe Queue
- **ProcessSnapshot**: Frozen dataclass with `__slots__` for memory efficiency

## License

MIT
