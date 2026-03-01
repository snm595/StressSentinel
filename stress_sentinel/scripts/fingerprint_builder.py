"""
Behavior Fingerprint Builder for StressSentinel.

Builds a baseline behavior fingerprint from collected runtime metrics
by computing mean and standard deviation for each metric dimension.
"""

import argparse
import json
import os

import numpy as np


# Metric keys to include in the fingerprint
_FINGERPRINT_KEYS = [
    "cpu_percent",
    "process_cpu_percent",
    "thread_count",
    "load_avg",
]

# Default output path for the fingerprint file
_DEFAULT_FINGERPRINT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "fingerprint.json",
)


def build_fingerprint(metrics: list) -> dict:
    """
    Build a behavior fingerprint from a list of metric records.

    Computes the mean and standard deviation for each metric dimension
    to create a statistical baseline of normal system behavior.

    Args:
        metrics: A list of metric record dicts, each containing keys:
                 timestamp, cpu_percent, process_cpu_percent,
                 thread_count, load_avg.

    Returns:
        A fingerprint dictionary mapping each metric to its mean and std.

    Raises:
        ValueError: If metrics list is empty or records are missing keys.
    """
    # Validate input
    if not metrics:
        raise ValueError("Metrics list must not be empty.")

    if not isinstance(metrics, list):
        raise ValueError("Metrics must be a list of dictionaries.")

    # Validate that all required keys are present in every record
    for i, record in enumerate(metrics):
        if not isinstance(record, dict):
            raise ValueError(f"Record at index {i} is not a dictionary.")
        for key in _FINGERPRINT_KEYS:
            if key not in record:
                raise ValueError(
                    f"Record at index {i} is missing required key: '{key}'"
                )

    fingerprint = {}

    for key in _FINGERPRINT_KEYS:
        # Extract values for this metric across all records
        values = np.array([record[key] for record in metrics], dtype=np.float64)

        # IQR-based outlier filtering: clip values outside [Q1-1.5*IQR, Q3+1.5*IQR]
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        filtered = values[(values >= lower) & (values <= upper)]

        # Fallback to original if all values were filtered out
        if len(filtered) == 0:
            filtered = values

        # Compute mean and standard deviation on clean data
        fingerprint[key] = {
            "mean": round(float(np.mean(filtered)), 6),
            "std": round(float(np.std(filtered)), 6),
        }

    return fingerprint


def save_fingerprint(fingerprint: dict, filepath: str = _DEFAULT_FINGERPRINT_PATH) -> None:
    """
    Save a fingerprint dictionary to a JSON file.

    Args:
        fingerprint: The fingerprint dictionary to save.
        filepath: Path to the output JSON file.
    """
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(fingerprint, f, indent=2)

    print(f"Fingerprint saved to: {filepath}")


def load_fingerprint(filepath: str = _DEFAULT_FINGERPRINT_PATH) -> dict:
    """
    Load a fingerprint dictionary from a JSON file.

    Args:
        filepath: Path to the fingerprint JSON file.

    Returns:
        The fingerprint dictionary.

    Raises:
        FileNotFoundError: If the fingerprint file does not exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Fingerprint file not found: {filepath}")

    with open(filepath, "r") as f:
        fingerprint = json.load(f)

    print(f"Fingerprint loaded from: {filepath}")
    return fingerprint


def _print_fingerprint(fingerprint: dict) -> None:
    """
    Print the fingerprint in a readable table format.

    Args:
        fingerprint: The fingerprint dictionary.
    """
    print(f"\n{'='*50}")
    print(f"  Behavior Fingerprint")
    print(f"{'='*50}")
    print(f"  {'Metric':<25} {'Mean':>10} {'Std':>10}")
    print(f"  {'-'*45}")
    for key, stats in fingerprint.items():
        print(f"  {key:<25} {stats['mean']:>10.4f} {stats['std']:>10.4f}")
    print(f"{'='*50}\n")


def main() -> None:
    """
    CLI entry point for the fingerprint builder.

    Usage:
        python fingerprint_builder.py --metrics-file <path>
    """
    parser = argparse.ArgumentParser(
        description="StressSentinel Behavior Fingerprint Builder — "
        "computes a baseline fingerprint from collected metrics."
    )
    parser.add_argument(
        "--metrics-file",
        type=str,
        required=True,
        help="Path to a JSON file containing a list of metric records.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=_DEFAULT_FINGERPRINT_PATH,
        help=f"Path to save the fingerprint JSON (default: data/fingerprint.json)",
    )

    args = parser.parse_args()

    # Load metrics from the provided JSON file
    if not os.path.exists(args.metrics_file):
        parser.error(f"Metrics file not found: {args.metrics_file}")

    with open(args.metrics_file, "r") as f:
        metrics = json.load(f)

    # Build the fingerprint
    fingerprint = build_fingerprint(metrics)

    # Display the fingerprint
    _print_fingerprint(fingerprint)

    # Save to disk
    save_fingerprint(fingerprint, filepath=args.output)


if __name__ == "__main__":
    main()
