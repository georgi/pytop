# 📄 pytop.spec.md

**Project:** `pytop` (Python System Monitor)
**Version:** 1.0.0-alpha
**Architecture Style:** Event-Driven / Reactive TUI
**Primary Objective:** Replicate `htop` fidelity with Python 3.14+ utilizing "Zero-Lag" UI principles.

---

## 1. 🛑 System Invariants (The "Iron Laws")

*The Agent must verify these constraints in every build step. Violation = Build Failure.*

1. **The 60Hz UI Rule:** The Interface Thread (UI) must remain responsive even if the Data Thread (Polling) hangs. UI rendering must be decoupled from `psutil` calls.
2. **Memory Cap:** The application must strictly stay under **50MB RSS** (Resident Set Size). Use `__slots__` on all data classes.
3. **Permission Grace:** The app must never crash due to `AccessDenied` or `ZombieProcess` exceptions. These must be handled silently with default values.
4. **Precision:** CPU usage percentages must match kernel time deltas (via `/proc/stat` logic) to within .
5. **Zero-Flicker:** Screen updates must use "Double Buffering" or differential repainting (provided by `Textual`).

---

## 2. 🏗️ Tech Stack & Dependencies

* **Runtime:** Python 3.13+ (Free-threaded / No-GIL mode preferred if available, otherwise strict threading).
* **Data Engine:** `psutil` (v6.0+) - utilizing `oneshot()` context managers for all iterators.
* **UI Framework:** `Textual` (for DOM-like TUI) OR `Rich` (for rendering). Preference: **Textual** for event loops.

---

## 3. 🧠 Data Architecture

### 3.1 The Process Entity (`Snapshot`)

*Draft Note: Use `dataclass(frozen=True)` to ensure immutability during rendering passes.*

```python
@dataclass(slots=True, frozen=True)
class ProcessSnapshot:
    pid: int
    name: str
    username: str
    status: str              # 'R', 'S', 'Z', 'D', etc.
    cpu_percent: float       # 0.0 - 100.0 * core_count
    memory_percent: float
    memory_rss: int          # Bytes
    threads: int
    nice: int
    command_line: str

```

### 3.2 Global State Store

The application state must be stored in a thread-safe `Reactive` model.

* **`cpu_history`**: `Deque[float]` (maxlen=60) - Per core history for sparklines.
* **`process_table`**: `List[ProcessSnapshot]` - Sorted and filtered list.
* **`sort_key`**: `Enum` (CPU | MEM | PID | USER) - Default: CPU.
* **`poll_rate`**: `float` - Default 2.0s (configurable).

---

## 4. ⚙️ Core Algorithms

### 4.1 The "Jitter-Free" Polling Loop

To prevent the "observer effect" (where measuring CPU usage spikes CPU usage), the polling logic must:

1. **Background Thread:** Run `psutil.process_iter()` in a `daemon` thread.
2. **Context Manager:** Wrap logic in `with process.oneshot():` to retrieve all attributes in a single syscall.
3. **Diffing Strategy:**
* *Previous State:* 
* *Current State:* 
* *Calculation:* Only update the UI if .


4. **Zombie Protection:** Wrap the iteration in a `try/except (psutil.NoSuchProcess)` block to handle processes dying mid-poll.

### 4.2 The "Visual" CPU Bar Calculation

Standard `psutil.cpu_percent()` is blocking. The agent must implement a **non-blocking** version:

* Store `psutil.cpu_times()` result from the previous tick.
* On current tick, fetch new times.
* Compute delta manually:



---

## 5. 🖥️ UI/UX Specification (The "Vibe")

### 5.1 Layout Grid

The TUI must mimic the classic 3-pane layout:

```
+---------------------------------------------------------------+
| [Header Area: 25% height]                                     |
| - Left: CPU Bars (1 per core, colored Green/Red)              |
| - Right: Memory Swap / Load Avg / Uptime                      |
+---------------------------------------------------------------+
| [Process List: Auto-fill height]                              |
| PID  USER      PRI  NI  VIRT   RES   SHR S  CPU%  MEM%  CMD |
| 101  root       20   0  100M   10M    4M S   0.0   0.1  init|
| ...  (Scrollable, Virtualized DOM)                            |
+---------------------------------------------------------------+
| [Footer: 1 line]                                              |
| F1Help  F2Setup  F3Search  F4Filter  F5Tree  F6Sort ...       |
+---------------------------------------------------------------+

```

### 5.2 Color Palette (ANSI Compliant)

* **CPU User:** `Bright Green` (#00FF00)
* **CPU System:** `Red` (#FF0000)
* **Memory Used:** `Cyan` (#00FFFF)
* **Memory Cache:** `Yellow` (#FFFF00)
* **Highlight Row:** `Bold Black` on `Cyan Background`

### 5.3 Key Bindings (Event Handlers)

* `F9` / `k`: Trigger "Kill Menu" (Signal selection modal).
* `F6` / `>`: Cycle Sort Column (CPU -> MEM -> TIME -> PID).
* `/`: Focus "Search Input" widget (filters process list by regex).
* `q`: Graceful shutdown (cancel threads, flush buffers, exit code 0).

---

## 6. 🧪 Verification Suite (Agent Self-Test)

Before marking the task as complete, the Agent must generate and pass the following tests:

1. **Load Test:** Spawn 5,000 dummy processes (using `multiprocessing`). Ensure UI FPS > 30.
2. **Chaos Monkey:** Randomly terminate processes while the monitor is running. Ensure no `NoSuchProcess` crash.
3. **Leak Check:** Run for 60 seconds. Ensure RAM usage delta is < 1MB.

---

## 7. 🚀 Implementation

**Phase 1: Skeleton**

> "Scaffold a `Textual` app with a Header, Data Table, and Footer. Mock the data. Ensure the layout resizes correctly on window change."

**Phase 2: The Engine**

> "Implement the `SystemMonitor` class using `psutil`. It must run in a separate `threading.Thread` and push updates to a thread-safe `Queue`. Handle `AccessDenied` errors gracefully."

**Phase 3: The Glue**

> "Connect the Queue to the Textual `DataTable`. Use `update_cell` for existing rows to avoid re-rendering the whole table (performance optimization)."

---
