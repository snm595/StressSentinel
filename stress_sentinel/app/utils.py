"""
Timing helpers and latency storage utilities.
"""

import time
from typing import List

# In-memory storage for latency records
_latency_records: List[float] = []


def get_high_res_time() -> float:
    """Return current time using high-resolution performance counter."""
    return time.perf_counter()


def record_latency(start_time: float, end_time: float) -> float:
    """
    Calculate latency in milliseconds from start and end times,
    store it, and return the value.
    """
    latency_ms = (end_time - start_time) * 1000.0
    _latency_records.append(latency_ms)
    return latency_ms


def get_all_latencies() -> List[float]:
    """Return a copy of all recorded latency values."""
    return list(_latency_records)


def clear_latencies() -> None:
    """Clear all stored latency records."""
    _latency_records.clear()
