"""
이 파일의 역할: 문법 질문 답변 API (PRD F6-4).  POST /grammar-qa  {question, native_language, student_level} → 답 + 근거
읽기만 한다 (DB에 쓰지 않음).
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.agent.grammar_qa import answer_question
from app.api.errors import error_info
from app.schemas.api import GrammarQaRequest

logger = logging.getLogger("ai_server.grammar_qa")
router = APIRouter(tags=["grammar_qa"])


@router.post("/grammar-qa")
def grammar_qa(req: GrammarQaRequest):
    # 동기 함수라 FastAPI가 스레드풀에서 실행한다 (이벤트 루프를 막지 않음)
    try:
        return answer_question(req.question, req.native_language, req.student_level)
    except Exception as exc:
        logger.exception("grammar_qa failed")
        return JSONResponse(status_code=502, content=error_info(exc))
