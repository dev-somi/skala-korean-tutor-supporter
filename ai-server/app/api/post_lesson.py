"""
이 파일의 역할: 수업 후 기록 그래프(post_lesson)를 API로 실행한다.

  POST /post-lesson  {profile, lesson, raw_note, current_weaknesses} → SSE
    started → node_finished … → done {record_draft, warnings, validation, rewrite_count}
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agent.post_lesson.graph import make_initial_state
from app.agent.post_lesson.schemas import PostLessonRequest
from app.api.errors import error_info
from app.schemas.api import sse

logger = logging.getLogger("ai_server.post_lesson")
router = APIRouter(tags=["post-lesson"])

NODE_LABELS = {
    "extract": "수업 메모 정리",
    "gate": "교재 ID·약점 검사",
    "write_feedback": "피드백 메시지 쓰기",
    "validate": "피드백 메시지 검토",
}
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


async def run_stream(graph, initial: dict):
    yield sse("started", {})
    final: dict = dict(initial)
    try:
        async for chunk in graph.astream(initial, {"run_name": "post_lesson"}, stream_mode="updates"):
            for node, update in chunk.items():
                final.update(update or {})
                yield sse("node_finished", {"node": node, "label": NODE_LABELS.get(node, node)})
        yield sse(
            "done",
            {
                "record_draft": {**final["extraction"], "feedback_message": final["feedback_message"]},
                "warnings": final.get("warnings", []),
                "validation": final.get("validation"),
                "rewrite_count": final.get("rewrite_count", 0),
            },
        )
    except Exception as exc:
        logger.exception("post_lesson graph failed")
        yield sse("error", error_info(exc))


@router.post("/post-lesson")
async def post_lesson(req: PostLessonRequest, request: Request):
    graph = request.app.state.post_lesson_graph
    return StreamingResponse(run_stream(graph, make_initial_state(req)), media_type="text/event-stream", headers=SSE_HEADERS)
