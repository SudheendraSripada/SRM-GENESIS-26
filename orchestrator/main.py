"""
FastAPI Orchestrator Service.
Provides REST, Server-Sent Events (SSE), and WebSocket endpoints for managing
the autonomous performance testing pipeline state machine.
Runs on port 8001.
"""

import asyncio
from contextlib import asynccontextmanager
import json
from typing import List, Optional
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from orchestrator.models import (
    AgentEvent,
    CreateRunRequest,
    RunDetail,
    RunState,
    RunSummary,
)
from orchestrator.db import Database
from orchestrator.event_bus import EventBus
from orchestrator.engine import OrchestratorEngine

db = Database()
event_bus = EventBus()
engine = OrchestratorEngine(db=db, event_bus=event_bus)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.init_db()
    yield
    # Shutdown


app = FastAPI(
    title="Autonomous Performance Testing Orchestrator API",
    version="1.0.0",
    description="Owns the performance testing run state machine, connects agents with validators, and streams timeline events.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "orchestrator", "port": 8001}


@app.post("/api/v1/runs", response_model=RunSummary, status_code=status.HTTP_201_CREATED)
async def create_run(req: CreateRunRequest):
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    summary = await db.create_run(
        run_id=run_id,
        prompt=req.prompt,
        mock_mode=req.mock_mode,
    )
    # Kick off background state machine
    engine.start_run(run_id=run_id, prompt=req.prompt, mock_mode=req.mock_mode)
    return summary


@app.get("/api/v1/runs", response_model=List[RunSummary])
async def list_runs(limit: int = 50):
    return await db.list_runs(limit=limit)


@app.get("/api/v1/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: str):
    detail = await db.get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return detail


@app.post("/api/v1/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    cancelled = await engine.cancel_run(run_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Run is not actively executing or could not be cancelled")
    return {"status": "cancelled", "run_id": run_id}


@app.get("/api/v1/runs/{run_id}/events")
async def stream_run_events(run_id: str):
    """Server-Sent Events endpoint streaming live AgentEvents for a run."""
    run_detail = await db.get_run_detail(run_id)
    if not run_detail:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    async def event_generator():
        # First send all historical events
        past_events = await db.get_events(run_id)
        for pe in past_events:
            yield {
                "event": pe.event_type,
                "data": pe.model_dump_json(),
            }

        # If already in a terminal state, close stream
        if run_detail.state in (
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.BLOCKED,
            RunState.CANCELLED,
            RunState.TIMEOUT,
        ):
            return

        # Subscribe to live events
        queue = await event_bus.subscribe(run_id)
        try:
            while True:
                try:
                    event: AgentEvent = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event.event_type,
                        "data": event.model_dump_json(),
                    }
                    if event.state in (
                        RunState.COMPLETED,
                        RunState.FAILED,
                        RunState.BLOCKED,
                        RunState.CANCELLED,
                        RunState.TIMEOUT,
                    ):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive comment
                    yield {":": "keep-alive"}
        finally:
            await event_bus.unsubscribe(run_id, queue)

    return EventSourceResponse(event_generator())


@app.websocket("/api/v1/runs/{run_id}/ws")
async def websocket_run_events(websocket: WebSocket, run_id: str):
    """WebSocket endpoint streaming live AgentEvents for a run."""
    await websocket.accept()
    run_detail = await db.get_run_detail(run_id)
    if not run_detail:
        await websocket.send_text(json.dumps({"error": f"Run '{run_id}' not found"}))
        await websocket.close()
        return

    # Send historical events first
    past_events = await db.get_events(run_id)
    for pe in past_events:
        await websocket.send_text(pe.model_dump_json())

    # If already terminal, close gracefully
    if run_detail.state in (
        RunState.COMPLETED,
        RunState.FAILED,
        RunState.BLOCKED,
        RunState.CANCELLED,
        RunState.TIMEOUT,
    ):
        await websocket.close()
        return

    queue = await event_bus.subscribe(run_id)
    try:
        while True:
            event: AgentEvent = await queue.get()
            await websocket.send_text(event.model_dump_json())
            if event.state in (
                RunState.COMPLETED,
                RunState.FAILED,
                RunState.BLOCKED,
                RunState.CANCELLED,
                RunState.TIMEOUT,
            ):
                break
    except WebSocketDisconnect:
        pass
    finally:
        await event_bus.unsubscribe(run_id, queue)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orchestrator.main:app", host="0.0.0.0", port=8001, reload=True)
