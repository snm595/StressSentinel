# Target Service

A FastAPI-based backend service that simulates CPU-bound request processing and measures request latency with high-resolution timers.

## What It Does

The Target Service exposes a `/process` endpoint that performs real CPU-intensive mathematical computations (trigonometric, logarithmic, and inverse trigonometric operations) to simulate workload processing. Each request's latency is measured using high-resolution performance counters and stored in memory for later retrieval.

## How to Run

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at `http://localhost:8000`.

### 3. API Documentation

Interactive docs are available at `http://localhost:8000/docs`.

## Example Requests

### Process a Request (Default Iterations)

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Process a Request (Custom Iterations)

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"iterations": 50000}'
```

**Response:**

```json
{
  "request_start_time": 123456.789,
  "request_end_time": 123456.912,
  "latency_ms": 123.456,
  "iterations": 50000,
  "status": "completed"
}
```

### Retrieve All Recorded Latencies

```bash
curl http://localhost:8000/latencies
```

**Response:**

```json
{
  "count": 2,
  "latencies_ms": [123.456, 98.765]
}
```

## Requirements

- Python 3.10+
- FastAPI
- Uvicorn

---

## CPU Stress Injector

A standalone script that introduces controlled CPU stress using multiprocessing workers. Each worker runs a tight mathematical computation loop to realistically consume CPU resources.

### How to Run

```bash
cd stress_sentinel
python scripts/stress_injector.py --duration 5 --workers 4
```

| Argument     | Description                              | Default |
|--------------|------------------------------------------|---------|
| `--duration` | Duration of stress in seconds            | 5       |
| `--workers`  | Number of parallel CPU worker processes  | 2       |

### Example

```bash
# Run 4 workers for 10 seconds
python scripts/stress_injector.py --duration 10 --workers 4
```

> **⚠️ Warning:** This script intentionally consumes significant CPU resources. The number of workers is automatically capped to your available CPU cores, but running it may still cause system slowdown. Avoid running on production machines.

---

## Metrics Collector

A standalone script that continuously samples runtime system metrics using `psutil`. Collected data is saved as structured JSON. The first sample is automatically discarded to avoid noise from `psutil` priming.

### Metrics Collected

| Metric                | Description                                      |
|-----------------------|--------------------------------------------------|
| `cpu_percent`         | Total system CPU usage percentage                |
| `process_cpu_percent` | CPU usage of the current Python process          |
| `thread_count`        | Number of threads in the current process         |
| `load_avg`            | System load average over the last 1 minute       |

### How to Run

```bash
cd stress_sentinel
pip install -r requirements.txt
python scripts/metrics_collector.py --duration 10 --interval 200 --output data/baseline_metrics.json
```

| Argument     | Description                              | Required |
|--------------|------------------------------------------|----------|
| `--duration` | Duration of collection in seconds        | Yes      |
| `--interval` | Sampling interval in milliseconds        | Yes      |
| `--output`   | Path to save the metrics JSON file       | Yes      |

### Example

```bash
# Collect metrics every 500ms for 30 seconds
python scripts/metrics_collector.py --duration 30 --interval 500 --output data/baseline_metrics.json
```

---

## Behavior Fingerprint Builder

A behavior fingerprint is a statistical baseline representing normal system behavior. It is computed from runtime metrics collected under controlled (non-stressed) conditions, capturing the **mean** and **standard deviation** for each metric dimension: `cpu_percent`, `process_cpu_percent`, `thread_count`, and `load_avg`. Outliers are automatically filtered using the **IQR method** (interquartile range) before computing statistics, so single spikes don't skew the baseline.

### How to Generate

**Step 1:** Collect baseline metrics (save output to a JSON file):

```bash
# First, collect metrics and save to a file
python -c "
import json
from scripts.metrics_collector import collect_metrics
records = collect_metrics(duration_seconds=30, interval_ms=200)
with open('data/baseline_metrics.json', 'w') as f:
    json.dump(records, f, indent=2)
"
```

**Step 2:** Build the fingerprint from collected metrics:

```bash
python scripts/fingerprint_builder.py --metrics-file data/baseline_metrics.json
```

The fingerprint will be saved to `data/fingerprint.json`.

| Argument         | Description                                 | Required |
|------------------|---------------------------------------------|----------|
| `--metrics-file` | Path to JSON file with metric records       | Yes      |
| `--output`       | Custom output path for the fingerprint JSON | No       |

---

## Anomaly Detector

Detects abnormal runtime behavior by comparing current metrics against a stored baseline fingerprint.

### How It Works

For each metric (`cpu_percent`, `process_cpu_percent`, `thread_count`, `load_avg`), the detector computes a **z-score**:

```
z = |value - mean| / std
```

Where `mean` and `std` come from the baseline fingerprint. A **minimum std floor** of `0.01` is applied so that metrics with zero baseline variance (e.g., a constant `thread_count`) can still trigger anomalies if they deviate.

### What Triggers an Alert

An anomaly is flagged when **at least 3 consecutive samples** exceed the z-score threshold (default: **2.5**). This consistency rule prevents single-sample spikes from causing false alerts.

### How to Run

```bash
cd stress_sentinel
python scripts/anomaly_detector.py \
  --metrics-file data/stressed_metrics.json \
  --fingerprint-file data/fingerprint.json \
  --threshold 2.5
```

| Argument              | Description                                 | Required | Default |
|-----------------------|---------------------------------------------|----------|---------|
| `--metrics-file`      | Path to JSON file with current metric data  | Yes      | —       |
| `--fingerprint-file`  | Path to the baseline fingerprint JSON       | Yes      | —       |
| `--threshold`         | Z-score threshold for anomaly detection     | No       | 2.5     |

---

## Full Experiment Runner

The experiment runner orchestrates the complete StressSentinel pipeline in a single command.

### Workflow

1. **Collect baseline metrics** — Samples system CPU, process CPU, thread count, and load average under normal conditions
2. **Build behavior fingerprint** — Computes mean and standard deviation per metric to establish a baseline
3. **Apply CPU stress + collect metrics** — Runs stress workers while simultaneously sampling metrics
4. **Run anomaly detection** — Compares stressed metrics against the baseline fingerprint using z-scores
5. **Generate visualizations** — Produces PNG plots comparing baseline vs stressed behavior
6. **Print summary** — Displays a comprehensive results overview in the console

### How to Run

```bash
cd stress_sentinel
pip install -r requirements.txt
python scripts/run_experiment.py \
  --baseline-duration 10 \
  --stress-duration 5 \
  --interval 200 \
  --workers 2
```

| Argument              | Description                                  | Default |
|-----------------------|----------------------------------------------|---------|
| `--baseline-duration` | Seconds to collect baseline metrics          | 10      |
| `--stress-duration`   | Seconds to run CPU stress                    | 5       |
| `--interval`          | Metrics sampling interval in milliseconds    | 200     |
| `--workers`           | Number of CPU stress worker processes        | 2       |

### Output Files

All output is saved to the `data/` directory:

| File                          | Description                                      |
|-------------------------------|--------------------------------------------------|
| `fingerprint.json`           | Baseline behavior fingerprint                    |
| `stressed_metrics.json`      | Raw metric records collected under stress        |
| `cpu_usage_over_time.png`    | System CPU usage: baseline vs stressed timeline  |
| `process_cpu_over_time.png`  | Process CPU usage: baseline vs stressed timeline |
| `latency_distribution.png`  | Distribution comparison of CPU and load average  |

### Interpreting Results

- **✅ No anomaly detected** — Stressed metrics remained within normal variance of the baseline fingerprint
- **⚠️ Anomaly detected** — One or more metrics had ≥3 consecutive samples exceeding the z-score threshold (default 2.5), indicating statistically significant deviation from normal behavior
- **Max Z-Score** — The highest deviation observed; higher values indicate stronger anomalies
- **Violated Metrics** — Which specific metrics triggered the alert (e.g., `cpu_percent`, `load_avg`)
