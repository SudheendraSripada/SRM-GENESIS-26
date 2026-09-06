"""
Safe Demo Target API for Antigravity AI Performance Testing Platform.
Runs on port 8080.
Provides lightweight endpoints (/health, /api/auth/login, /api/products, /api/checkout)
with configurable latency and error rates for benchmark testing.
"""

import asyncio
import os
import random
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Genesis Performance Demo API",
    version="1.0.0",
    description="Safe local target application for k6 load and stress testing.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurable chaos parameters
DEFAULT_LATENCY_MS = float(os.getenv("DEMO_API_LATENCY_MS", "25.0"))
DEFAULT_ERROR_RATE = float(os.getenv("DEMO_API_ERROR_RATE", "0.001"))

# Request models
class LoginRequest(BaseModel):
    username: str = "demo_user"
    password: str = "demo_pass"

class CheckoutRequest(BaseModel):
    cart_id: Optional[str] = "cart_demo_1001"
    items: Optional[List[Dict[str, Any]]] = None
    payment_token: Optional[str] = "tok_demo_token"


async def simulate_workload(
    chaos_enabled: bool = False,
    extra_delay_ms: float = 0.0,
):
    """Simulates realistic server latency and optional error injection."""
    base_latency = DEFAULT_LATENCY_MS
    jitter = random.uniform(-5.0, 15.0)
    delay_ms = max(5.0, base_latency + jitter + extra_delay_ms)

    # Random jitter or chaos latency injection
    if chaos_enabled:
        delay_ms += random.uniform(200.0, 800.0)

    await asyncio.sleep(delay_ms / 1000.0)

    # Chaos error injection
    error_threshold = 0.20 if chaos_enabled else DEFAULT_ERROR_RATE
    if random.random() < error_threshold:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulated internal service degradation error",
        )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "demo-target-api",
        "timestamp": time.time(),
        "default_latency_ms": DEFAULT_LATENCY_MS,
        "default_error_rate": DEFAULT_ERROR_RATE,
    }


@app.post("/api/auth/login")
@app.post("/login")
async def login(
    req: Optional[LoginRequest] = None,
    chaos: bool = Query(default=False),
):
    await simulate_workload(chaos_enabled=chaos)
    return {
        "status": "authenticated",
        "user_id": "usr_99812",
        "token": "tok_demo_jwt_session_token_xyz987",
        "expires_in": 3600,
    }


@app.get("/api/products")
@app.get("/products")
async def get_products(
    limit: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = None,
    chaos: bool = Query(default=False),
):
    await simulate_workload(chaos_enabled=chaos)
    products = [
        {
            "id": f"prod_{i:04d}",
            "name": f"Enterprise Cloud Node {i}",
            "price": round(49.99 + (i * 2.5), 2),
            "in_stock": True,
            "category": category or "infrastructure",
        }
        for i in range(1, limit + 1)
    ]
    return {
        "count": len(products),
        "products": products,
        "page": 1,
    }


@app.post("/api/checkout")
@app.post("/checkout")
async def checkout(
    req: Optional[CheckoutRequest] = None,
    authorization: Optional[str] = Header(default=None),
    chaos: bool = Query(default=False),
):
    # Checkout is heavier: add 20ms base delay
    await simulate_workload(chaos_enabled=chaos, extra_delay_ms=20.0)

    order_id = f"ord_{int(time.time() * 1000)}_{random.randint(100, 999)}"
    return {
        "status": "confirmed",
        "order_id": order_id,
        "total_amount": 129.95,
        "currency": "USD",
        "cart_id": req.cart_id if req else "cart_default",
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
