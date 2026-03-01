"""
CPU Stress Injector for StressSentinel.

Introduces controlled CPU stress using multiprocessing workers
that perform tight computational loops for a configurable duration.
"""

import argparse
import math
import multiprocessing
import os
import time


def _cpu_worker(duration_seconds: int, stop_event: multiprocessing.Event) -> None:
    """
    A single CPU-bound worker that runs a tight computation loop.

    Performs continuous mathematical operations (sqrt, sin, cos, log, atan2)
    until the specified duration elapses or the stop event is set.

    Args:
        duration_seconds: Maximum number of seconds this worker should run.
        stop_event: Shared event that signals all workers to terminate.
    """
    end_time = time.monotonic() + duration_seconds
    counter = 0

    # Tight CPU loop — performs real math to consume CPU cycles
    while time.monotonic() < end_time and not stop_event.is_set():
        counter += 1
        # Deterministic math operations that consume CPU
        _ = math.sqrt(counter) * math.sin(counter) * math.cos(counter)
        _ = math.log(counter + 1)
        _ = math.atan2(counter, counter + 1)

        # Periodically check termination conditions (every 10,000 iterations)
        # to balance responsiveness with computational throughput
        if counter % 10_000 == 0:
            if stop_event.is_set():
                break


def run_cpu_stress(duration_seconds: int, workers: int) -> None:
    """
    Run CPU stress for a fixed duration using multiple parallel workers.

    Each worker is a separate process that performs tight CPU-bound
    computation loops. All workers are terminated cleanly when the
    duration expires.

    Args:
        duration_seconds: How long (in seconds) to run the stress test.
        workers: Number of parallel CPU worker processes to spawn.
    """
    # Cap workers to available CPU cores to avoid over-subscription
    available_cores = os.cpu_count() or 1
    if workers > available_cores:
        print(
            f"Warning: Requested {workers} workers but only {available_cores} "
            f"CPU cores available. Capping to {available_cores}."
        )
        workers = available_cores

    print(f"Starting CPU stress: {workers} worker(s) for {duration_seconds} second(s)")

    # Shared event to signal all workers to stop
    stop_event = multiprocessing.Event()

    # Spawn worker processes
    processes = []
    for i in range(workers):
        p = multiprocessing.Process(
            target=_cpu_worker,
            args=(duration_seconds, stop_event),
            name=f"stress-worker-{i}",
        )
        processes.append(p)

    # Start all workers
    for p in processes:
        p.start()

    try:
        # Wait for the specified duration
        time.sleep(duration_seconds)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Shutting down workers...")
    finally:
        # Signal all workers to stop
        stop_event.set()

        # Wait for all workers to finish with a timeout
        for p in processes:
            p.join(timeout=5)

        # Force-terminate any workers that didn't exit cleanly
        for p in processes:
            if p.is_alive():
                print(f"Force-terminating worker: {p.name}")
                p.terminate()
                p.join(timeout=2)

    print("CPU stress completed.")


def main() -> None:
    """
    CLI entry point for the stress injector.

    Usage:
        python stress_injector.py --duration 5 --workers 4
    """
    parser = argparse.ArgumentParser(
        description="StressSentinel CPU Stress Injector — "
        "introduces controlled CPU load using multiprocessing workers."
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Duration of stress in seconds (default: 5)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of parallel CPU worker processes (default: 2)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.duration <= 0:
        parser.error("--duration must be a positive integer")
    if args.workers <= 0:
        parser.error("--workers must be a positive integer")

    run_cpu_stress(duration_seconds=args.duration, workers=args.workers)


if __name__ == "__main__":
    main()
