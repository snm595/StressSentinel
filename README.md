# StressSentinel 🛡️

A real-time system monitoring dashboard that visualizes CPU usage, thread count, and load averages with anomaly detection capabilities.

## Features

- **Real-time Dashboard**: Live system metrics visualization with 1-second refresh
- **Anomaly Detection**: Statistical analysis to detect unusual system behavior
- **Stress Testing**: Built-in CPU stress injector for testing
- **Professional UI**: Modern dark theme with interactive charts
- **File-based Architecture**: Simple JSON-based data storage

## Architecture

```
StressSentinel/
├── stress_sentinel/
│   ├── dashboard.py          # Enhanced Streamlit dashboard
│   ├── app/                  # FastAPI target service
│   ├── scripts/              # Utility scripts
│   │   ├── metrics_collector.py
│   │   ├── stress_injector.py
│   │   ├── anomaly_detector.py
│   │   └── fingerprint_builder.py
│   ├── data/                 # Data storage
│   └── requirements.txt
└── README.md
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install streamlit-autorefresh
```

### 2. Start the Dashboard
```bash
cd stress_sentinel
streamlit run dashboard.py
```

### 3. Collect Live Metrics
```bash
python scripts/metrics_collector.py \
  --duration 60 \
  --interval 1000 \
  --output data/baseline_metrics.json \
  --live-output data/live_metrics.json
```

### 4. Apply Stress (Optional)
```bash
python scripts/stress_injector.py --duration 10 --workers 4
```

## Dashboard Features

### Real-time Monitoring
- System CPU usage
- Process CPU usage  
- Thread count
- Load average (1-minute)

### Interactive Elements
- Rolling time windows (30s, 60s, 120s)
- Live status indicators (Healthy/Under Stress/Anomaly)
- Smart insights based on metric trends
- Enhanced charts with statistics

### Visual Design
- Modern dark theme
- Color-coded metrics (warm for CPU, cool for system)
- Smooth animations and hover effects
- Professional layout for demos

## Scripts Overview

### `metrics_collector.py`
Collects system metrics using `psutil`:
```bash
python scripts/metrics_collector.py --duration 30 --interval 500 --output data/metrics.json
```

### `stress_injector.py`
Applies controlled CPU stress:
```bash
python scripts/stress_injector.py --duration 5 --workers 2
```

### `anomaly_detector.py`
Detects statistical anomalies:
```bash
python scripts/anomaly_detector.py --metrics-file data/stressed_metrics.json --fingerprint-file data/fingerprint.json
```

### `fingerprint_builder.py`
Creates baseline behavior fingerprint:
```bash
python scripts/fingerprint_builder.py --metrics-file data/baseline_metrics.json
```

### `run_experiment.py`
Complete pipeline automation:
```bash
python scripts/run_experiment.py --baseline-duration 10 --stress-duration 5 --interval 200 --workers 2
```

## API Service

Start the FastAPI target service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API endpoints:
- `POST /process` - CPU-intensive task processing
- `GET /latencies` - Retrieve recorded latencies

## Data Format

### Metrics JSON
```json
[
  {
    "timestamp": 1234567890.123,
    "cpu_percent": 25.5,
    "process_cpu_percent": 15.2,
    "thread_count": 8,
    "load_avg": 1.25
  }
]
```

### Fingerprint JSON
```json
{
  "cpu_percent": {"mean": 15.2, "std": 5.1},
  "process_cpu_percent": {"mean": 8.5, "std": 2.3},
  "thread_count": {"mean": 8, "std": 0},
  "load_avg": {"mean": 1.2, "std": 0.3}
}
```

## Technology Stack

- **Backend**: Python, FastAPI, psutil
- **Frontend**: Streamlit, streamlit-autorefresh
- **Data**: JSON file storage
- **Analytics**: pandas, numpy
- **Visualization**: Streamlit charts

## Use Cases

- **System Monitoring**: Real-time performance tracking
- **Load Testing**: Stress testing and capacity planning
- **Anomaly Detection**: Identifying unusual system behavior
- **Demo Applications**: Technical presentations and hackathons
- **Educational**: Learning about system metrics and monitoring

## Configuration

### Dashboard Settings
- Refresh interval: 1 second (configurable)
- Time windows: 30s, 60s, 120s
- Status thresholds: CPU > 70%, Load > 2.0

### Anomaly Detection
- Z-score threshold: 2.5 (configurable)
- Consecutive samples: 3 required
- IQR filtering for baseline

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

---

**StressSentinel** - Real-time system monitoring made simple and professional.
