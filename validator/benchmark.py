import time
import json
from app.engine.pipeline_orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator()

# Test payloads of various shapes and failure modes
payloads = {
    "Golden Stress Spec (Valid)": {
        "version": "1.0",
        "metadata": {"name": "Auth Stress"},
        "test": {"type": "stress"},
        "target": {"base_url": "https://example.com", "endpoint": "/login", "method": "POST"},
        "load": {"start_vus": 10, "target_vus": 100, "duration_seconds": 180},
        "stages": [
            {"duration_seconds": 60, "target_vus": 30},
            {"duration_seconds": 60, "target_vus": 70},
            {"duration_seconds": 60, "target_vus": 100}
        ],
        "headers": {"Content-Type": "application/json"},
        "payload": {"type": "json", "body": {"user": "alice", "pass": "secret"}},
        "thresholds": [{"metric": "http_req_duration", "percentile": 95, "operator": "<", "value": 300}]
    },
    "Markdown Fenced + Syntax Malformed": """```json
{
  "test": {"type": "load",},
  "target": {"base_url": "https://example.com",}
}
```""",
    "Semantic Stress Inversion (Decreasing)": {
        "version": "1.0",
        "test": {"type": "stress"},
        "target": {"base_url": "https://example.com", "method": "GET"},
        "load": {"start_vus": 200, "target_vus": 50, "duration_seconds": 120},
        "stages": [
            {"duration_seconds": 60, "target_vus": 200},
            {"duration_seconds": 60, "target_vus": 50}
        ]
    },
    "Cross-Field Duration Mismatch": {
        "version": "1.0",
        "target": {"base_url": "https://example.com", "method": "GET"},
        "load": {"start_vus": 5, "target_vus": 20, "duration_seconds": 300},
        "stages": [
            {"duration_seconds": 60, "target_vus": 10},
            {"duration_seconds": 60, "target_vus": 20}
        ]
    },
    "Security SSRF + High VUs Attack": {
        "version": "1.0",
        "test": {"type": "stress"},
        "target": {"base_url": "http://169.254.169.254", "endpoint": "/latest", "method": "GET"},
        "load": {"start_vus": 5000, "target_vus": 25000, "duration_seconds": 7200}
    },
    "Large Multi-Stage Packet (15 stages)": {
        "version": "1.0",
        "test": {"type": "stress"},
        "target": {"base_url": "https://example.com", "endpoint": "/items", "method": "POST"},
        "load": {"start_vus": 5, "target_vus": 150, "duration_seconds": 150},
        "stages": [{"duration_seconds": 10, "target_vus": 10 * i} for i in range(1, 16)],
        "headers": {f"X-Custom-Header-{i}": f"value-{i}" for i in range(20)},
        "payload": {"type": "json", "body": {"batch": list(range(50))}}
    }
}

print(f"{'Test Payload Name':<42} | {'Verdict':<8} | {'Score':<6} | {'Avg Latency (μs)':<16} | {'Throughput (ops/sec)':<20}")
print("-" * 105)

ITERATIONS = 1000

for name, packet in payloads.items():
    # Warmup
    orchestrator.run(packet)

    start = time.perf_counter()
    for _ in range(ITERATIONS):
        res = orchestrator.run(packet)
    total_time = time.perf_counter() - start

    avg_us = (total_time / ITERATIONS) * 1_000_000
    ops_sec = ITERATIONS / total_time
    print(f"{name:<42} | {res.status.value:<8} | {res.validation_score:<6} | {avg_us:>14.2f} μs | {ops_sec:>18.1f} ops/s")
