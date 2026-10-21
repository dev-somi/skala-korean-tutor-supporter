"""
이 파일의 역할: LangSmith에 쌓인 실행 기록(trace)을 읽어서 화면용으로 돌려준다 (기술 ADR-0028).

  GET /traces?limit=30&name=lesson_prep&errors_only=false   최근 실행 목록 + 요약
  GET /traces/{trace_id}                                    실행 하나의 트리 (그래프 노드 → 함수 → LLM 호출)

LangSmith 키는 ai-server의 .env에만 있다. 화면은 Spring(/api/traces)을 거쳐 여기를 부른다 (ADR-0005).
추적이 꺼져 있으면 {"enabled": false}만 돌려준다.
"""

import json
import logging
import os
from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from langsmith import Client
from langsmith.utils import tracing_is_enabled

from app.api import post_lesson, prep

logger = logging.getLogger("ai_server.traces")
router = APIRouter(tags=["traces"])

# 실행 이름 → 화면에 보일 한글 이름. 그래프 노드 이름은 진행 표시에 쓰던 표를 그대로 쓴다
ROOT_LABELS = {
    "lesson_prep": "수업 준비",
    "post_lesson": "수업 후 기록",
    "student_intake": "학생 등록",
    "grammar_qa": "문법 질문",
}
LABELS = {**prep.NODE_LABELS, **post_lesson.NODE_LABELS, **ROOT_LABELS}
PREVIEW_CHARS = 2000


def tracing_enabled() -> bool:
    has_key = bool(os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY"))
    return has_key and bool(tracing_is_enabled())


def project_name() -> str:
    return os.environ.get("LANGSMITH_PROJECT") or os.environ.get("LANGCHAIN_PROJECT") or "default"


@lru_cache
def get_client() -> Client:
    return Client()


def langsmith_error(exc: Exception) -> JSONResponse:
    # LangSmith 연결·키 문제는 우리 그래프 오류가 아니라 바깥 서비스 문제라 다시 시도할 수 있게 둔다
    content = {"code": "LANGSMITH_ERROR", "message": f"{type(exc).__name__}: {exc}", "retryable": True}
    return JSONResponse(status_code=502, content=content)


def ms_between(start, end) -> int | None:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds() * 1000)


def preview(value) -> str | None:
    """입력·출력을 화면에 보여 줄 만큼만 자른 JSON 글"""
    if not value:
        return None
    text = json.dumps(value, ensure_ascii=False, default=str, indent=1)
    return text if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS] + " …(생략)"


def run_url(run) -> str | None:
    """LangSmith 웹에서 이 실행을 여는 주소"""
    if not getattr(run, "app_path", None):
        return None
    host = getattr(get_client(), "_host_url", None) or "https://smith.langchain.com"
    return host.rstrip("/") + run.app_path


def status_of(run) -> str:
    if run.error:
        return "error"
    return "success" if run.end_time else "running"


def summarize_run(run) -> dict:
    """목록 한 줄"""
    metadata = (run.extra or {}).get("metadata", {})
    return {
        "id": str(run.id),
        "trace_id": str(run.trace_id),
        "name": run.name,
        "label": LABELS.get(run.name, run.name),
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "latency_ms": ms_between(run.start_time, run.end_time),
        "status": status_of(run),
        "error": run.error,
        "total_tokens": run.total_tokens or 0,
        "prompt_tokens": run.prompt_tokens or 0,
        "completion_tokens": run.completion_tokens or 0,
        "total_cost": float(run.total_cost) if run.total_cost is not None else None,
        "thread_id": metadata.get("thread_id"),
        "url": run_url(run),
    }


def summary_of(rows: list[dict]) -> dict:
    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    costs = [r["total_cost"] for r in rows if r["total_cost"] is not None]
    return {
        "count": len(rows),
        "errors": sum(r["status"] == "error" for r in rows),
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "total_tokens": sum(r["total_tokens"] for r in rows),
        # 로컬 Ollama는 비용이 없다 (null)
        "total_cost": round(sum(costs), 6) if costs else None,
    }


def build_tree(runs: list) -> dict | None:
    """
    한 trace의 run 전체를 parent_run_id로 이어 트리로 만든다.
    start_offset_ms는 맨 위 실행이 시작한 때부터 몇 ms 뒤에 시작했는지 (화면의 시간 막대 위치).
    """
    if not runs:
        return None
    root = next((r for r in runs if r.parent_run_id is None), min(runs, key=lambda r: r.start_time))
    nodes = {}
    for run in runs:
        metadata = (run.extra or {}).get("metadata", {})
        nodes[run.id] = {
            "id": str(run.id),
            "name": run.name,
            "label": LABELS.get(run.name, run.name),
            "run_type": run.run_type,
            "start_offset_ms": ms_between(root.start_time, run.start_time) or 0,
            "latency_ms": ms_between(run.start_time, run.end_time),
            "status": status_of(run),
            "error": run.error,
            "total_tokens": run.total_tokens or 0,
            "model": metadata.get("ls_model_name") or metadata.get("model"),
            "inputs": preview(run.inputs),
            "outputs": preview(run.outputs),
            "_start": run.start_time,
            "children": [],
        }
    for run in runs:
        if run.id != root.id and run.parent_run_id in nodes:
            nodes[run.parent_run_id]["children"].append(nodes[run.id])

    def finish(node: dict) -> dict:
        node["children"].sort(key=lambda c: c["_start"])
        node.pop("_start")
        for child in node["children"]:
            finish(child)
        return node

    tree = finish(nodes[root.id])
    return {**summarize_run(root), "total_latency_ms": tree["latency_ms"], "root": tree}


@router.get("/traces")
def list_traces(
    limit: int = Query(default=30, ge=1, le=100),
    name: str | None = Query(default=None, pattern=r"^[a-z_]{1,40}$"),
    errors_only: bool = False,
):
    if not tracing_enabled():
        return {"enabled": False, "project": project_name()}
    try:
        runs = get_client().list_runs(
            project_name=project_name(),
            is_root=True,
            limit=limit,
            filter=f'eq(name, "{name}")' if name else None,
            error=True if errors_only else None,
        )
        rows = [summarize_run(r) for r in runs]
    except Exception as exc:
        logger.exception("langsmith list_runs failed")
        return langsmith_error(exc)
    return {"enabled": True, "project": project_name(), "summary": summary_of(rows), "runs": rows}


@router.get("/traces/{trace_id}")
def get_trace(trace_id: UUID):
    if not tracing_enabled():
        return {"enabled": False, "project": project_name()}
    try:
        runs = list(get_client().list_runs(project_name=project_name(), trace_id=trace_id))
    except Exception as exc:
        logger.exception("langsmith trace read failed")
        return langsmith_error(exc)
    tree = build_tree(runs)
    if tree is None:
        return JSONResponse(status_code=404, content={"code": "TRACE_NOT_FOUND", "message": "실행 기록을 찾을 수 없습니다", "retryable": False})
    return {"enabled": True, "project": project_name(), **tree}
