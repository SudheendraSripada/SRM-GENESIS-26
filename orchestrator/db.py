"""
SQLite persistence layer for the Orchestrator service.
Maintains runs, run artifacts, and historical event logs using aiosqlite.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite

from orchestrator.models import AgentEvent, RunDetail, RunState, RunSummary

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "runs.db"


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """Initializes SQLite schema and creates tables if they do not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    state TEXT NOT NULL,
                    mock_mode INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    error_message TEXT
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS run_artifacts (
                    run_id TEXT PRIMARY KEY,
                    requirement_spec TEXT,
                    performance_plan TEXT,
                    test_data_plan TEXT,
                    test_specification TEXT,
                    adapted_test_spec TEXT,
                    critic_result TEXT,
                    validation_result TEXT,
                    compiled_k6_script TEXT,
                    execution_result TEXT,
                    analysis_result TEXT,
                    decision_result TEXT,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, id);")
            await db.commit()

    async def _ensure_initialized(self):
        await self.init_db()

    async def create_run(self, run_id: str, prompt: str, mock_mode: bool = True) -> RunSummary:
        await self.init_db()
        now = datetime.now(timezone.utc).isoformat()
        state = RunState.CREATED.value
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO runs (run_id, prompt, state, mock_mode, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, prompt, state, 1 if mock_mode else 0, now, now),
            )
            await db.execute(
                "INSERT INTO run_artifacts (run_id) VALUES (?)",
                (run_id,),
            )
            await db.commit()

        return RunSummary(
            run_id=run_id,
            prompt=prompt,
            state=RunState.CREATED,
            mock_mode=mock_mode,
            created_at=now,
            updated_at=now,
        )

    async def update_run_state(
        self,
        run_id: str,
        state: RunState,
        error_message: Optional[str] = None,
    ):
        now = datetime.now(timezone.utc).isoformat()
        completed_at = now if state in (
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.BLOCKED,
            RunState.CANCELLED,
            RunState.TIMEOUT,
        ) else None

        async with aiosqlite.connect(self.db_path) as db:
            if completed_at:
                await db.execute(
                    """
                    UPDATE runs
                    SET state = ?, updated_at = ?, completed_at = ?, error_message = coalesce(?, error_message)
                    WHERE run_id = ?
                    """,
                    (state.value, now, completed_at, error_message, run_id),
                )
            else:
                await db.execute(
                    """
                    UPDATE runs
                    SET state = ?, updated_at = ?, error_message = coalesce(?, error_message)
                    WHERE run_id = ?
                    """,
                    (state.value, now, error_message, run_id),
                )
            await db.commit()

    async def save_artifact(self, run_id: str, field_name: str, data: Any):
        """Stores a serialized JSON or text artifact against the run."""
        serialized = data if isinstance(data, str) else json.dumps(data)
        allowed_columns = {
            "requirement_spec",
            "performance_plan",
            "test_data_plan",
            "test_specification",
            "adapted_test_spec",
            "critic_result",
            "validation_result",
            "compiled_k6_script",
            "execution_result",
            "analysis_result",
            "decision_result",
        }
        if field_name not in allowed_columns:
            raise ValueError(f"Invalid artifact column '{field_name}'")

        query = f"UPDATE run_artifacts SET {field_name} = ? WHERE run_id = ?"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, (serialized, run_id))
            await db.commit()

    async def save_event(self, event: AgentEvent):
        """Persists an AgentEvent to the historical log."""
        details_json = json.dumps(event.details) if event.details else "{}"
        event_id = event.event_id or f"evt_{datetime.now(timezone.utc).timestamp()}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO events (event_id, run_id, state, event_type, source, timestamp, message, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event.run_id,
                    event.state.value if hasattr(event.state, "value") else str(event.state),
                    event.event_type,
                    event.source,
                    event.timestamp,
                    event.message,
                    details_json,
                ),
            )
            await db.commit()

    async def get_events(self, run_id: str) -> List[AgentEvent]:
        """Retrieves all historical events for a run in order."""
        events = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT event_id, run_id, state, event_type, source, timestamp, message, details
                FROM events WHERE run_id = ? ORDER BY id ASC
                """,
                (run_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    details = json.loads(row[7]) if row[7] else {}
                    events.append(
                        AgentEvent(
                            event_id=row[0],
                            run_id=row[1],
                            state=RunState(row[2]),
                            event_type=row[3],
                            source=row[4],
                            timestamp=row[5],
                            message=row[6],
                            details=details,
                        )
                    )
        return events

    async def list_runs(self, limit: int = 50) -> List[RunSummary]:
        await self.init_db()
        runs = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT run_id, prompt, state, mock_mode, created_at, updated_at, completed_at, error_message
                FROM runs ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                for r in rows:
                    runs.append(
                        RunSummary(
                            run_id=r[0],
                            prompt=r[1],
                            state=RunState(r[2]),
                            mock_mode=bool(r[3]),
                            created_at=r[4],
                            updated_at=r[5],
                            completed_at=r[6],
                            error_message=r[7],
                        )
                    )
        return runs

    async def get_run_detail(self, run_id: str) -> Optional[RunDetail]:
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT r.run_id, r.prompt, r.state, r.mock_mode, r.created_at, r.updated_at, r.completed_at, r.error_message,
                       a.requirement_spec, a.performance_plan, a.test_data_plan, a.test_specification,
                       a.adapted_test_spec, a.critic_result, a.validation_result, a.compiled_k6_script,
                       a.execution_result, a.analysis_result, a.decision_result
                FROM runs r
                LEFT JOIN run_artifacts a ON r.run_id = a.run_id
                WHERE r.run_id = ?
                """,
                (run_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

        events = await self.get_events(run_id)

        def _parse(val: Optional[str]) -> Optional[Any]:
            if not val:
                return None
            try:
                return json.loads(val)
            except Exception:
                return val

        return RunDetail(
            run_id=row[0],
            prompt=row[1],
            state=RunState(row[2]),
            mock_mode=bool(row[3]),
            created_at=row[4],
            updated_at=row[5],
            completed_at=row[6],
            error_message=row[7],
            requirement_spec=_parse(row[8]),
            performance_plan=_parse(row[9]),
            test_data_plan=_parse(row[10]),
            test_specification=_parse(row[11]),
            adapted_test_spec=_parse(row[12]),
            critic_result=_parse(row[13]),
            validation_result=_parse(row[14]),
            compiled_k6_script=row[15],
            execution_result=_parse(row[16]),
            analysis_result=_parse(row[17]),
            decision_result=_parse(row[18]),
            events=events,
        )
