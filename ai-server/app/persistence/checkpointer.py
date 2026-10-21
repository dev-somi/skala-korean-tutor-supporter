"""
이 파일의 역할: LangGraph checkpointer를 만드는 단 한 곳 (참고노트 3-4).

HITL(human_review)에서 멈췄다가 다른 요청으로 이어 가려면 그래프 상태를 저장해야 한다.
저장소를 바꿀 때(SQLite → Postgres, ADR-0002 재검토 조건) 이 파일만 고친다.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.lesson_prep.textbook import PROJECT_DIR


@asynccontextmanager
async def create_checkpointer(path: str | None = None):
    """CHECKPOINT_DB 환경변수(기본: output/checkpoints.db)에 상태를 저장하는 checkpointer. 테스트는 ":memory:"."""
    path = path or os.environ.get("CHECKPOINT_DB", str(PROJECT_DIR / "output" / "checkpoints.db"))
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        yield saver
