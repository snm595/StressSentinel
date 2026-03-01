"""
Request processing logic and CPU simulation function.
"""

import math
from app.utils import get_high_res_time, record_latency


def simulate_cpu_work(iterations: int = 100_000) -> float:
    """
    Simulate CPU-bound work using mathematical operations.
    Performs a series of trigonometric and logarithmic computations.

    Args:
        iterations: Number of computation iterations to perform.

    Returns:
        A dummy result value from the computation.
    """
    result = 0.0
    for i in range(1, iterations + 1):
        result += math.sqrt(i) * math.sin(i) * math.cos(i)
        result += math.log(i + 1)
        result += math.atan2(i, i + 1)
    return result


def process_request(iterations: int = 100_000) -> dict:
    """
    Process a single request by simulating CPU-bound work and
    recording the latency.

    Args:
        iterations: Number of computation iterations (controls processing time).

    Returns:
        A dictionary containing request timing details.
    """
    start_time = get_high_res_time()

    # Perform CPU-bound simulation
    _ = simulate_cpu_work(iterations)

    end_time = get_high_res_time()

    # Record and retrieve latency
    latency_ms = record_latency(start_time, end_time)

    return {
        "request_start_time": start_time,
        "request_end_time": end_time,
        "latency_ms": round(latency_ms, 3),
        "iterations": iterations,
        "status": "completed",
    }
