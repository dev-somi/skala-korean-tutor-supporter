"""
이 파일의 역할: 수업 준비 그래프(lesson_prep)를 API로 실행한다. 진행 상황은 SSE로 보낸다.

  POST /prep/start              그래프 시작 → … review_required 에서 멈춤
  POST /prep/{thread_id}/resume 선생님 결정으로 재개 → review_required 또는 done
  GET  /prep/{thread_id}/state  지금 상태 다시 받기 (화면 새로고침 대비)
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from app.agent.lesson_prep.graph import make_initial_state
from app.agent.lesson_prep.schemas import CATEGORIES
from app.api.errors import error_info
from app.schemas.api import PrepResumeRequest, PrepStartRequest, sse

logger = logging.getLogger("ai_server.prep")
router = APIRouter(prefix="/prep", tags=["prep"])

# 화면의 진행 단계 표시에 쓰는 노드 이름
NODE_LABELS = {
    "load_profile": "학생 프로필 읽기",
    "load_textbook": "교재 읽기",
    "plan_lesson": "수업 구성안 만들기",
    "write_explanations": "개인화 설명 쓰기",
    "write_scripts": "대본 쓰기",
    "auto_review": "자동 검토",
    "briefing": "선생님 브리핑 만들기",
    "write_slides": "15장 슬라이드 구성안 쓰기",
    "write_slide_scripts": "장별 수업 대본 쓰기",
    "human_review": "선생님 검토 반영",
}

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def config_for(thread_id: str) -> dict:
    # run_name·metadata는 LangSmith 추적에서 이 실행을 찾는 이름표 (기술 ADR-0028)
    return {"configurable": {"thread_id": thread_id}, "run_name": "lesson_prep", "metadata": {"thread_id": thread_id}}


def done_payload(thread_id: str, values: dict) -> dict:
    """확정된 수업안. PPT는 만들지 않으므로(ADR-0015) 파일 칸은 항상 비어 있다 (Spring 응답 형식 호환)."""
    drafts = values.get("drafts", {})
    return {
        "thread_id": thread_id,
        "pptx_file": None,
        "pdf_file": None,
        "plan": {c: {k: drafts[c][k] for k in ("item_ids", "minutes", "reason")} for c in CATEGORIES if c in drafts},
        "drafts": drafts,
        "briefing": values.get("briefing"),
    }


def pending_interrupt(snapshot) -> dict | None:
    """멈춰 있는 human_review의 interrupt 값. 없으면 None."""
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


async def run_stream(graph, graph_input, thread_id: str):
    """그래프를 실행하면서 노드가 끝날 때마다 SSE 이벤트를 만든다."""
    config = config_for(thread_id)
    yield sse("started", {"thread_id": thread_id})
    try:
        async for chunk in graph.astream(graph_input, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    yield sse("review_required", {"thread_id": thread_id, **update[0].value})
                else:
                    yield sse("node_finished", {"thread_id": thread_id, "node": node, "label": NODE_LABELS.get(node, node)})
        snapshot = await graph.aget_state(config)
        if not snapshot.next:
            yield sse("done", done_payload(thread_id, snapshot.values))
    except Exception as exc:  # 어떤 오류든 스트림 안에서 error 이벤트로 알린다
        logger.exception("prep graph failed", extra={"thread_id": thread_id})
        yield sse("error", {"thread_id": thread_id, **error_info(exc)})


@router.post("/start")
async def start(req: PrepStartRequest, request: Request):
    graph = request.app.state.prep_graph
    initial = make_initial_state(
        student_id=req.profile.student_id,
        unit_no=req.unit_no,
        book=req.book,
        target_lang=req.target_lang,
        lesson_minutes=req.lesson_minutes,
        profile=req.profile.model_dump(),
        output_subdir=req.output_subdir,
    )
    return StreamingResponse(run_stream(graph, initial, req.thread_id), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/{thread_id}/resume")
async def resume(thread_id: str, req: PrepResumeRequest, request: Request):
    graph = request.app.state.prep_graph
    snapshot = await graph.aget_state(config_for(thread_id))
    if not snapshot.values:
        raise HTTPException(404, "thread not found")
    if pending_interrupt(snapshot) is None:
        raise HTTPException(409, "thread is not waiting for review")
    # exclude_none: edit에서 보내지 않은 칸은 기존 초안을 유지한다 (human_review 참고)
    decisions = {c: d.model_dump(exclude_none=True) for c, d in req.decisions.items()}
    return StreamingResponse(
        run_stream(graph, Command(resume=decisions), thread_id), media_type="text/event-stream", headers=SSE_HEADERS
    )


@router.get("/{thread_id}/state")
async def state(thread_id: str, request: Request):
    graph = request.app.state.prep_graph
    snapshot = await graph.aget_state(config_for(thread_id))
    if not snapshot.values:
        raise HTTPException(404, "thread not found")
    payload = pending_interrupt(snapshot)
    if payload is not None:
        return {"status": "review_required", "thread_id": thread_id, **payload}
    if snapshot.next:
        return {"status": "running", "thread_id": thread_id}
    return {"status": "done", **done_payload(thread_id, snapshot.values)}
