"""
Anomaly Detector for StressSentinel.

Detects abnormal runtime behavior by comparing current metrics against
a stored baseline fingerprint using z-score deviation analysis.
"""

import argparse
import json
import os

import numpy as np


# Metric keys to evaluate for anomalies
_METRIC_KEYS = [
    "cpu_percent",
    "process_cpu_percent",
    "thread_count",
    "load_avg",
]

# Minimum consecutive samples exceeding threshold to flag an anomaly
_CONSECUTIVE_REQUIRED = 3

# Minimum std floor to avoid division-by-zero and catch deviations
# on metrics that were constant during baseline collection.
_MIN_STD = 0.01


def _compute_z_scores(values: list, mean: float, std: float) -> list:
    """
    Compute z-scores for a list of values given a baseline mean and std.

    z = |value - mean| / std

    Uses a minimum std floor so that metrics with zero variance in the
    baseline can still trigger anomalies if they deviate.

    Args:
        values: List of observed metric values.
        mean: Baseline mean from the fingerprint.
        std: Baseline standard deviation from the fingerprint.

    Returns:
        A list of z-score floats.
    """
    effective_std = max(std, _MIN_STD)

    arr = np.array(values, dtype=np.float64)
    z_scores = np.abs(arr - mean) / effective_std
    return z_scores.tolist()


def _has_consecutive_violations(z_scores: list, threshold: float, required: int = _CONSECUTIVE_REQUIRED) -> bool:
    """
    Check if there are at least `required` consecutive z-scores
    that exceed the threshold.

    Args:
        z_scores: List of z-score values.
        threshold: The z-score threshold to consider a violation.
        required: Number of consecutive violations needed.

    Returns:
        True if a consecutive violation streak is found.
    """
    if len(z_scores) < required:
        return False

    consecutive = 0
    for z in z_scores:
        if z > threshold:
            consecutive += 1
            if consecutive >= required:
                return True
        else:
            # Reset streak on non-violation
            consecutive = 0

    return False


def detect_anomaly(
    metrics: list,
    fingerprint: dict,
    threshold: float = 2.5,
) -> dict:
    """
    Detect anomalies by comparing current metrics against a baseline fingerprint.

    For each metric dimension, computes z-scores and checks whether at least
    3 consecutive samples exceed the given threshold.

    Args:
        metrics: A list of current metric record dicts.
        fingerprint: A baseline fingerprint dict with mean/std per metric.
        threshold: Z-score threshold for violation (default: 2.5).

    Returns:
        A dict with:
            anomaly_detected (bool): Whether any metric is anomalous.
            violated_metrics (list): Names of metrics that triggered alerts.
            max_z_score (float): The highest z-score observed across all metrics.

    Raises:
        ValueError: If metrics list is empty or inputs are invalid.
    """
    if not metrics:
        raise ValueError("Metrics list must not be empty.")

    if not fingerprint:
        raise ValueError("Fingerprint must not be empty.")

    violated_metrics = []
    global_max_z = 0.0

    for key in _METRIC_KEYS:
        # Skip metrics not present in the fingerprint
        if key not in fingerprint:
            continue

        fp = fingerprint[key]
        mean = fp["mean"]
        std = fp["std"]

        # Extract values for this metric from all records
        values = [record[key] for record in metrics]

        # Compute z-scores
        z_scores = _compute_z_scores(values, mean, std)

        # Track the maximum z-score across all metrics
        max_z = float(np.max(z_scores))
        if max_z > global_max_z:
            global_max_z = max_z

        # Check for consecutive violations
        if _has_consecutive_violations(z_scores, threshold):
            violated_metrics.append(key)

    return {
        "anomaly_detected": len(violated_metrics) > 0,
        "violated_metrics": violated_metrics,
        "max_z_score": round(global_max_z, 4),
    }


def _print_result(result: dict) -> None:
    """
    Print the anomaly detection result in a readable format.

    Args:
        result: The detection result dictionary.
    """
    print(f"\n{'='*50}")
    print(f"  Anomaly Detection Result")
    print(f"{'='*50}")

    if result["anomaly_detected"]:
        print(f"  ⚠️  ANOMALY DETECTED")
        print(f"  Violated Metrics : {', '.join(result['violated_metrics'])}")
    else:
        print(f"  ✅  No anomaly detected")

    print(f"  Max Z-Score      : {result['max_z_score']}")
    print(f"{'='*50}\n")


def main() -> None:
    """
    CLI entry point for the anomaly detector.

    Usage:
        python anomaly_detector.py --metrics-file <path> --fingerprint-file <path>
    """
    parser = argparse.ArgumentParser(
        description="StressSentinel Anomaly Detector — "
        "compares current metrics against a baseline fingerprint."
    )
    parser.add_argument(
        "--metrics-file",
        type=str,
        required=True,
        help="Path to a JSON file containing current metric records.",
    )
    parser.add_argument(
        "--fingerprint-file",
        type=str,
        required=True,
        help="Path to the baseline fingerprint JSON file.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=2.5,
        help="Z-score threshold for anomaly detection (default: 2.5).",
    )

    args = parser.parse_args()

    # Validate file paths
    if not os.path.exists(args.metrics_file):
        parser.error(f"Metrics file not found: {args.metrics_file}")
    if not os.path.exists(args.fingerprint_file):
        parser.error(f"Fingerprint file not found: {args.fingerprint_file}")

    # Load inputs
    with open(args.metrics_file, "r") as f:
        metrics = json.load(f)

    with open(args.fingerprint_file, "r") as f:
        fingerprint = json.load(f)

    # Run detection
    result = detect_anomaly(
        metrics=metrics,
        fingerprint=fingerprint,
        threshold=args.threshold,
    )

    _print_result(result)


if __name__ == "__main__":
    main()
