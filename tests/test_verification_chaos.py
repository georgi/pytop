"""Verification Test: Chaos Monkey - Random process termination resilience.

Per pytop.spec.md Section 6 "Verification Suite":
- Randomly terminate processes from dummy processes while the monitor is running
- Ensure no NoSuchProcess crash

This tests the "Permission Grace" invariant from Section 1:
"The app must never crash due to AccessDenied or ZombieProcess exceptions."
"""

import multiprocessing
import random
import time
from queue import Empty, Queue

import pytest

from pytop.monitor import SystemMonitor, SystemSnapshot


def dummy_worker(duration: float = 60.0) -> None:
    """A dummy worker process that sleeps for a given duration."""
    try:
        time.sleep(duration)
    except (KeyboardInterrupt, SystemExit):
        pass


class TestChaosMonkey:
    """Chaos Monkey verification suite tests."""

    def test_monitor_survives_process_termination(self):
        """
        Test that the monitor doesn't crash when processes die mid-poll.

        This simulates the real-world scenario where processes can terminate
        at any time during monitoring. The monitor must handle NoSuchProcess
        exceptions gracefully without crashing.
        """
        # Spawn dummy processes
        processes = []
        num_processes = 50

        for _ in range(num_processes):
            p = multiprocessing.Process(target=dummy_worker, args=(60.0,))
            p.start()
            processes.append(p)

        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.3)

        try:
            monitor.start()

            # Get initial snapshot to confirm monitor is working
            snapshot = queue.get(timeout=5.0)
            assert snapshot is not None

            # Randomly terminate processes while monitor is running
            processes_to_kill = random.sample(processes, min(25, len(processes)))

            for p in processes_to_kill:
                if p.is_alive():
                    p.terminate()
                # Small delay to spread out terminations
                time.sleep(0.05)

            # Continue collecting snapshots - monitor should not crash
            snapshots_after_chaos = 0
            start_time = time.time()
            max_wait = 5.0

            while time.time() - start_time < max_wait:
                try:
                    snapshot = queue.get(timeout=1.0)
                    snapshots_after_chaos += 1
                    # Verify snapshot is valid
                    assert isinstance(snapshot.processes, list)
                except Empty:
                    continue
                except Exception as e:
                    pytest.fail(f"Monitor crashed with exception: {e}")

            # Monitor should have continued providing snapshots
            assert snapshots_after_chaos >= 3, (
                f"Expected at least 3 snapshots after chaos, got {snapshots_after_chaos}"
            )

            # Verify monitor is still running
            assert monitor.is_running, "Monitor should still be running after chaos"

        finally:
            monitor.stop()
            # Clean up all processes
            for p in processes:
                if p.is_alive():
                    p.terminate()
            for p in processes:
                p.join(timeout=1.0)

    def test_rapid_process_creation_and_termination(self):
        """
        Test monitor stability during rapid process churn.

        This tests a more extreme scenario where processes are rapidly
        created and destroyed, simulating a highly dynamic system.
        """
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.2)

        processes = []
        exceptions_caught = []

        try:
            monitor.start()

            # Run chaos for a few seconds
            start_time = time.time()
            duration = 3.0

            while time.time() - start_time < duration:
                try:
                    # Create new processes
                    for _ in range(5):
                        p = multiprocessing.Process(target=dummy_worker, args=(10.0,))
                        p.start()
                        processes.append(p)

                    # Kill some random processes
                    alive_processes = [p for p in processes if p.is_alive()]
                    if len(alive_processes) > 10:
                        to_kill = random.sample(alive_processes, min(3, len(alive_processes)))
                        for p in to_kill:
                            p.terminate()

                    # Small delay
                    time.sleep(0.1)

                except Exception as e:
                    exceptions_caught.append(e)

            # Verify monitor survived the chaos
            assert monitor.is_running, "Monitor crashed during rapid churn"

            # Collect final snapshot
            final_snapshot = None
            try:
                final_snapshot = queue.get(timeout=3.0)
            except Empty:
                pass

            assert final_snapshot is not None, "Monitor stopped providing snapshots"

        finally:
            monitor.stop()
            # Clean up
            for p in processes:
                if p.is_alive():
                    p.terminate()
            for p in processes:
                p.join(timeout=0.5)

    def test_collect_processes_handles_terminated_process(self):
        """
        Test that _collect_processes handles NoSuchProcess gracefully.

        This directly tests the process collection method's resilience
        to processes disappearing mid-iteration.
        """
        # Create and immediately terminate a process
        p = multiprocessing.Process(target=dummy_worker, args=(60.0,))
        p.start()

        # Give it a moment to start
        time.sleep(0.1)

        # Terminate it
        p.terminate()
        p.join(timeout=1.0)

        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=1.0)

        # This should not raise an exception
        try:
            processes = monitor._collect_processes()
            # The terminated process should not be in the list (or if it is, it's fine)
            # The important thing is no exception was raised
            assert isinstance(processes, list)
        except Exception as e:
            pytest.fail(f"_collect_processes raised an exception: {e}")

    def test_zombie_process_handling(self):
        """
        Test that the monitor handles zombie processes gracefully.

        Zombie processes can occur when a child process terminates but
        the parent hasn't waited for it yet. The monitor must not crash
        when encountering zombies.
        """
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.5)

        monitor.start()

        try:
            # Create and terminate a process without joining (potential zombie)
            p = multiprocessing.Process(target=dummy_worker, args=(0.1,))
            p.start()

            # Wait for it to complete naturally
            time.sleep(0.3)

            # Collect snapshots - should not crash on zombie
            for _ in range(3):
                try:
                    snapshot = queue.get(timeout=2.0)
                    assert isinstance(snapshot.processes, list)
                except Empty:
                    continue

            # Clean up the zombie
            p.join(timeout=1.0)

            assert monitor.is_running, "Monitor should survive zombie processes"

        finally:
            monitor.stop()

    def test_continuous_monitoring_during_chaos(self):
        """
        Test that the monitor continues to provide updates during chaos.

        This verifies the spec requirement that the monitoring loop
        continues running and providing data even when encountering errors.
        """
        queue: Queue[SystemSnapshot] = Queue()
        monitor = SystemMonitor(queue, poll_rate=0.2)
        processes = []

        try:
            monitor.start()

            # Spawn initial batch
            for _ in range(20):
                p = multiprocessing.Process(target=dummy_worker, args=(60.0,))
                p.start()
                processes.append(p)

            snapshot_times = []
            start_time = time.time()
            test_duration = 4.0

            while time.time() - start_time < test_duration:
                # Try to get snapshot
                try:
                    queue.get(timeout=0.5)
                    snapshot_times.append(time.time())
                except Empty:
                    pass

                # Randomly kill a process
                alive = [p for p in processes if p.is_alive()]
                if alive and random.random() < 0.3:
                    p = random.choice(alive)
                    p.terminate()

                # Randomly spawn a new one
                if random.random() < 0.2:
                    p = multiprocessing.Process(target=dummy_worker, args=(60.0,))
                    p.start()
                    processes.append(p)

            # Verify we got consistent updates throughout the test
            assert len(snapshot_times) >= 5, (
                f"Expected at least 5 snapshots during chaos, got {len(snapshot_times)}"
            )

            # Check that snapshots were distributed throughout the test period
            if len(snapshot_times) >= 2:
                time_span = snapshot_times[-1] - snapshot_times[0]
                assert time_span >= 1.0, "Snapshots should be distributed over time"

        finally:
            monitor.stop()
            for p in processes:
                if p.is_alive():
                    p.terminate()
            for p in processes:
                p.join(timeout=0.5)
