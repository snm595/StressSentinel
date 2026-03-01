"""
FastAPI application initialization and route definitions.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, List

from app.service import process_request
from app.utils import get_all_latencies

app = FastAPI(
    title="StressSentinel Target Service",
    description="A CPU-bound request processing service with latency measurement.",
    version="1.0.0",
)


class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""
    iterations: Optional[int] = Field(
        default=100_000,
        gt=0,
        description="Number of CPU computation iterations. Higher values increase processing time.",
    )


class ProcessResponse(BaseModel):
    """Response body for the /process endpoint."""
    request_start_time: float
    request_end_time: float
    latency_ms: float
    iterations: int
    status: str


class LatenciesResponse(BaseModel):
    """Response body for the /latencies endpoint."""
    count: int
    latencies_ms: List[float]


@app.post("/process", response_model=ProcessResponse)
def handle_process(request: ProcessRequest = ProcessRequest()):
    """
    Simulate CPU-bound request processing.

    Accepts an optional `iterations` parameter to control processing time.
    Records and returns latency information for each request.
    """
    result = process_request(iterations=request.iterations)
    return result


@app.get("/latencies", response_model=LatenciesResponse)
def handle_latencies():
    """
    Retrieve all recorded request latencies.
    """
    latencies = get_all_latencies()
    return {
        "count": len(latencies),
        "latencies_ms": latencies,
    }
