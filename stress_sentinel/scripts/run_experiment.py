"""
StressSentinel Experiment Runner.

Orchestrates the full end-to-end experiment:
1. Collect baseline metrics
2. Build behavior fingerprint
3. Apply CPU stress while collecting metrics
4. Run anomaly detection
5. Generate visualizations
"""

import argparse
import json
import os
import sys
import threading
import time

# Add project root to path so we can import sibling modules
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — no GUI windows
import matplotlib.pyplot as plt
import numpy as np

from scripts.metrics_collector import collect_metrics
from scripts.fingerprint_builder import build_fingerprint, save_fingerprint, load_fingerprint
from scripts.stress_injector import run_cpu_stress
from scripts.anomaly_detector import detect_anomaly


# Output paths
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_FINGERPRINT_PATH = os.path.join(_DATA_DIR, "fingerprint.json")
_STRESSED_METRICS_PATH = os.path.join(_DATA_DIR, "stressed_metrics.json")
_CPU_PLOT_PATH = os.path.join(_DATA_DIR, "cpu_usage_over_time.png")
_PROCESS_CPU_PLOT_PATH = os.path.join(_DATA_DIR, "process_cpu_over_time.png")
_LATENCY_DIST_PLOT_PATH = os.path.join(_DATA_DIR, "latency_distribution.png")


# ──────────────────────────────────────────────
# Visualization
# ──────────────────────────────────────────────

def _plot_cpu_usage(baseline: list, stressed: list, output_path: str) -> None:
    """
    Plot total CPU usage over time for baseline vs stressed periods.

    Args:
        baseline: List of baseline metric records.
        stressed: List of stressed metric records.
        output_path: File path to save the plot as PNG.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    # Baseline timeline (relative seconds from start)
    b_start = baseline[0]["timestamp"]
    b_times = [(r["timestamp"] - b_start) for r in baseline]
    b_cpu = [r["cpu_percent"] for r in baseline]

    # Stressed timeline (continue from where baseline ended)
    offset = b_times[-1] + 1.0  # gap for visual separation
    s_start = stressed[0]["timestamp"]
    s_times = [(r["timestamp"] - s_start) + offset for r in stressed]
    s_cpu = [r["cpu_percent"] for r in stressed]

    ax.plot(b_times, b_cpu, color="#2196F3", linewidth=1.5, label="Baseline", marker=".", markersize=3)
    ax.plot(s_times, s_cpu, color="#F44336", linewidth=1.5, label="Under Stress", marker=".", markersize=3)

    # Mark the separation
    ax.axvline(x=offset - 0.5, color="#9E9E9E", linestyle="--", alpha=0.6, label="Stress Applied")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("CPU Usage (%)")
    ax.set_title("System CPU Usage — Baseline vs Stressed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  → Saved: {output_path}")


def _plot_process_cpu(baseline: list, stressed: list, output_path: str) -> None:
    """
    Plot process CPU usage over time for baseline vs stressed periods.

    Args:
        baseline: List of baseline metric records.
        stressed: List of stressed metric records.
        output_path: File path to save the plot as PNG.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    b_start = baseline[0]["timestamp"]
    b_times = [(r["timestamp"] - b_start) for r in baseline]
    b_cpu = [r["process_cpu_percent"] for r in baseline]

    offset = b_times[-1] + 1.0
    s_start = stressed[0]["timestamp"]
    s_times = [(r["timestamp"] - s_start) + offset for r in stressed]
    s_cpu = [r["process_cpu_percent"] for r in stressed]

    ax.plot(b_times, b_cpu, color="#4CAF50", linewidth=1.5, label="Baseline", marker=".", markersize=3)
    ax.plot(s_times, s_cpu, color="#FF9800", linewidth=1.5, label="Under Stress", marker=".", markersize=3)

    ax.axvline(x=offset - 0.5, color="#9E9E9E", linestyle="--", alpha=0.6, label="Stress Applied")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Process CPU Usage (%)")
    ax.set_title("Process CPU Usage — Baseline vs Stressed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  → Saved: {output_path}")


def _plot_latency_distribution(baseline: list, stressed: list, output_path: str) -> None:
    """
    Plot latency distribution comparison between baseline and stressed periods.
    Uses CPU usage as a proxy for latency (since true request latency requires
    the target service to be actively handling requests).

    Args:
        baseline: List of baseline metric records.
        stressed: List of stressed metric records.
        output_path: File path to save the plot as PNG.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # CPU percent distribution
    b_cpu = [r["cpu_percent"] for r in baseline]
    s_cpu = [r["cpu_percent"] for r in stressed]

    axes[0].hist(b_cpu, bins=20, alpha=0.7, color="#2196F3", label="Baseline", edgecolor="white")
    axes[0].hist(s_cpu, bins=20, alpha=0.7, color="#F44336", label="Stressed", edgecolor="white")
    axes[0].set_xlabel("CPU Usage (%)")
    axes[0].set_ylabel("Frequency")
    axes[0].set_title("CPU Usage Distribution")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Load average distribution
    b_load = [r["load_avg"] for r in baseline]
    s_load = [r["load_avg"] for r in stressed]

    axes[1].hist(b_load, bins=20, alpha=0.7, color="#4CAF50", label="Baseline", edgecolor="white")
    axes[1].hist(s_load, bins=20, alpha=0.7, color="#FF9800", label="Stressed", edgecolor="white")
    axes[1].set_xlabel("Load Average (1 min)")
    axes[1].set_ylabel("Frequency")
    axes[1].set_title("Load Average Distribution")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.suptitle("Baseline vs Stressed — Distribution Comparison", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  → Saved: {output_path}")


# ──────────────────────────────────────────────
# Console Summary
# ──────────────────────────────────────────────

def _print_experiment_summary(
    baseline: list,
    stressed: list,
    fingerprint: dict,
    detection_result: dict,
) -> None:
    """Print a clear summary of the experiment results."""
    print(f"\n{'='*60}")
    print(f"  StressSentinel — Experiment Results")
    print(f"{'='*60}")

    # Baseline stats
    b_cpu = [r["cpu_percent"] for r in baseline]
    print(f"\n  📊 Baseline ({len(baseline)} samples)")
    print(f"     CPU %  : avg={np.mean(b_cpu):.1f}  min={np.min(b_cpu):.1f}  max={np.max(b_cpu):.1f}")

    # Stressed stats
    s_cpu = [r["cpu_percent"] for r in stressed]
    print(f"\n  🔥 Under Stress ({len(stressed)} samples)")
    print(f"     CPU %  : avg={np.mean(s_cpu):.1f}  min={np.min(s_cpu):.1f}  max={np.max(s_cpu):.1f}")

    # Fingerprint
    print(f"\n  🧬 Behavior Fingerprint")
    for key, stats in fingerprint.items():
        print(f"     {key:<25} mean={stats['mean']:.4f}  std={stats['std']:.4f}")

    # Detection
    print(f"\n  🔍 Anomaly Detection")
    if detection_result["anomaly_detected"]:
        print(f"     ⚠️  ANOMALY DETECTED")
        print(f"     Violated Metrics : {', '.join(detection_result['violated_metrics'])}")
    else:
        print(f"     ✅  No anomaly detected")
    print(f"     Max Z-Score      : {detection_result['max_z_score']}")

    print(f"\n  📈 Plots saved to: {_DATA_DIR}/")
    print(f"     • cpu_usage_over_time.png")
    print(f"     • process_cpu_over_time.png")
    print(f"     • latency_distribution.png")
    print(f"{'='*60}\n")


# ──────────────────────────────────────────────
# Orchestration
# ──────────────────────────────────────────────

def run_experiment(
    baseline_duration: int,
    stress_duration: int,
    interval_ms: int,
    stress_workers: int,
) -> None:
    """
    Run the full StressSentinel experiment.

    Steps:
        1. Collect baseline metrics (no stress)
        2. Build and save behavior fingerprint
        3. Apply CPU stress while collecting metrics simultaneously
        4. Run anomaly detection comparing stressed vs baseline
        5. Generate visualization plots
        6. Print experiment summary

    Args:
        baseline_duration: Seconds to collect baseline metrics.
        stress_duration: Seconds to run CPU stress.
        interval_ms: Metrics sampling interval in milliseconds.
        stress_workers: Number of CPU stress worker processes.
    """
    os.makedirs(_DATA_DIR, exist_ok=True)

    # ── Step 1: Collect baseline metrics ──
    print("\n" + "─" * 60)
    print("  STEP 1: Collecting baseline metrics")
    print("─" * 60)
    baseline_metrics = collect_metrics(
        duration_seconds=baseline_duration,
        interval_ms=interval_ms,
    )

    if not baseline_metrics:
        print("ERROR: No baseline metrics collected. Aborting.")
        return

    # ── Step 2: Build behavior fingerprint ──
    print("\n" + "─" * 60)
    print("  STEP 2: Building behavior fingerprint")
    print("─" * 60)
    fingerprint = build_fingerprint(baseline_metrics)
    save_fingerprint(fingerprint, filepath=_FINGERPRINT_PATH)

    # ── Step 3: Apply stress and collect metrics simultaneously ──
    print("\n" + "─" * 60)
    print("  STEP 3: Applying CPU stress + collecting metrics")
    print("─" * 60)

    # Run stress injector in a separate thread so we can collect metrics
    # in the main thread at the same time
    stress_thread = threading.Thread(
        target=run_cpu_stress,
        args=(stress_duration, stress_workers),
        name="stress-orchestrator",
    )
    stress_thread.start()

    # Give stress workers a moment to spin up before sampling
    time.sleep(0.5)

    # Collect metrics while stress is running
    stressed_metrics = collect_metrics(
        duration_seconds=stress_duration,
        interval_ms=interval_ms,
    )

    # Wait for stress to finish
    stress_thread.join()

    if not stressed_metrics:
        print("ERROR: No stressed metrics collected. Aborting.")
        return

    # Save stressed metrics to disk
    with open(_STRESSED_METRICS_PATH, "w") as f:
        json.dump(stressed_metrics, f, indent=2)
    print(f"Stressed metrics saved to: {_STRESSED_METRICS_PATH}")

    # ── Step 4: Run anomaly detection ──
    print("\n" + "─" * 60)
    print("  STEP 4: Running anomaly detection")
    print("─" * 60)
    fingerprint = load_fingerprint(filepath=_FINGERPRINT_PATH)
    detection_result = detect_anomaly(
        metrics=stressed_metrics,
        fingerprint=fingerprint,
    )

    # ── Step 5: Generate visualizations ──
    print("\n" + "─" * 60)
    print("  STEP 5: Generating visualizations")
    print("─" * 60)
    _plot_cpu_usage(baseline_metrics, stressed_metrics, _CPU_PLOT_PATH)
    _plot_process_cpu(baseline_metrics, stressed_metrics, _PROCESS_CPU_PLOT_PATH)
    _plot_latency_distribution(baseline_metrics, stressed_metrics, _LATENCY_DIST_PLOT_PATH)

    # ── Step 6: Print summary ──
    _print_experiment_summary(
        baseline=baseline_metrics,
        stressed=stressed_metrics,
        fingerprint=fingerprint,
        detection_result=detection_result,
    )


def main() -> None:
    """
    CLI entry point for the experiment runner.

    Usage:
        python run_experiment.py --baseline-duration 10 --stress-duration 5 --interval 200
    """
    parser = argparse.ArgumentParser(
        description="StressSentinel Experiment Runner — "
        "orchestrates the full end-to-end stress detection experiment."
    )
    parser.add_argument(
        "--baseline-duration",
        type=int,
        default=10,
        help="Duration for baseline metrics collection in seconds (default: 10).",
    )
    parser.add_argument(
        "--stress-duration",
        type=int,
        default=5,
        help="Duration for CPU stress in seconds (default: 5).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=200,
        help="Metrics sampling interval in milliseconds (default: 200).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of CPU stress worker processes (default: 2).",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.baseline_duration <= 0:
        parser.error("--baseline-duration must be a positive integer")
    if args.stress_duration <= 0:
        parser.error("--stress-duration must be a positive integer")
    if args.interval <= 0:
        parser.error("--interval must be a positive integer")
    if args.workers <= 0:
        parser.error("--workers must be a positive integer")

    run_experiment(
        baseline_duration=args.baseline_duration,
        stress_duration=args.stress_duration,
        interval_ms=args.interval,
        stress_workers=args.workers,
    )


if __name__ == "__main__":
    main()
