"""
Metrics Collector for StressSentinel.

Collects runtime system and process metrics at a configurable interval
and saves them as structured JSON.
"""

import argparse
import os
import tempfile
import time
import json
from typing import Optional

import psutil

# Maximum number of samples kept in the rolling live file
_LIVE_BUFFER_SIZE = 100


def _collect_single_sample(process: psutil.Process) -> dict:
    """
    Collect a single metrics sample.
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    process_cpu_percent = process.cpu_percent(interval=None)
    thread_count = process.num_threads()
    load_avg_1m = psutil.getloadavg()[0]

    return {
        "timestamp": time.time(),
        "cpu_percent": cpu_percent,
        "process_cpu_percent": process_cpu_percent,
        "thread_count": thread_count,
        "load_avg": load_avg_1m,
    }


def _write_live_file(records: list, path: str) -> None:
    """
    Atomically write the most recent samples to the live metrics file.
    Uses write-to-temp + rename to ensure the file always contains valid JSON.
    """
    recent = records[-_LIVE_BUFFER_SIZE:]
    dir_name = os.path.dirname(os.path.abspath(path))
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(recent, f, indent=2)
        os.replace(tmp_path, path)
    except OSError:
        # Non-critical — dashboard will simply show stale data
        pass


def collect_metrics(
    duration_seconds: int,
    interval_ms: int,
    live_output_path: Optional[str] = None,
) -> list:
    """
    Collect metrics for a fixed duration.

    If live_output_path is provided, the most recent 100 samples are
    written to that file on every sampling cycle for live visualization.
    """
    records = []
    interval_seconds = interval_ms / 1000.0
    process = psutil.Process()

    psutil.cpu_percent(interval=None)
    process.cpu_percent(interval=None)

    end_time = time.monotonic() + duration_seconds

    print(
        f"Collecting metrics for {duration_seconds}s "
        f"at {interval_ms}ms intervals..."
    )

    while time.monotonic() < end_time:
        records.append(_collect_single_sample(process))

        # Update rolling live file if requested
        if live_output_path:
            _write_live_file(records, live_output_path)

        remaining = end_time - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval_seconds, remaining))

    # Discard the first sample — it often carries a residual spike
    # from the psutil priming call and can skew fingerprint stats.
    if len(records) > 1:
        records = records[1:]

    print(f"Collection complete. {len(records)} samples recorded.")
    return records


def save_metrics(metrics: list, output_path: str) -> None:
    """
    Save metrics to a JSON file.
    """
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)


def print_summary(records: list) -> None:
    """
    Print a human readable summary.
    """
    if not records:
        print("No records collected.")
        return

    cpu = [r["cpu_percent"] for r in records]
    proc_cpu = [r["process_cpu_percent"] for r in records]
    threads = [r["thread_count"] for r in records]
    load = [r["load_avg"] for r in records]

    print("\n" + "=" * 50)
    print(f"  Metrics Summary ({len(records)} samples)")
    print("=" * 50)
    print(f"  System CPU %  : avg={sum(cpu)/len(cpu):.1f}  min={min(cpu):.1f}  max={max(cpu):.1f}")
    print(f"  Process CPU % : avg={sum(proc_cpu)/len(proc_cpu):.1f}  min={min(proc_cpu):.1f}  max={max(proc_cpu):.1f}")
    print(f"  Thread Count  : avg={sum(threads)/len(threads):.1f}  min={min(threads)}  max={max(threads)}")
    print(f"  Load Avg (1m) : avg={sum(load)/len(load):.2f}  min={min(load):.2f}  max={max(load):.2f}")
    print("=" * 50 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="StressSentinel Metrics Collector"
    )
    parser.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Metrics collection duration in seconds",
    )
    parser.add_argument(
        "--interval",
        type=int,
        required=True,
        help="Sampling interval in milliseconds",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to save metrics JSON",
    )
    parser.add_argument(
        "--live-output",
        type=str,
        default=None,
        help="Optional path to write a rolling live metrics JSON file",
    )

    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration must be positive")
    if args.interval <= 0:
        parser.error("--interval must be positive")

    records = collect_metrics(
        duration_seconds=args.duration,
        interval_ms=args.interval,
        live_output_path=args.live_output,
    )

    save_metrics(records, args.output)
    print_summary(records)


if __name__ == "__main__":
    main()