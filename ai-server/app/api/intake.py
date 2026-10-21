"""
이 파일의 역할: 학생 등록 초안 API.  POST /intake  {text} → {draft, warnings}
저장하지 않는다. 선생님이 확인한 뒤 Spring이 저장한다.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.agent.intake import IntakeResult, run_intake
from app.api.errors import error_info
from app.schemas.api import IntakeRequest

logger = logging.getLogger("ai_server.intake")
router = APIRouter(tags=["intake"])


@router.post("/intake", response_model=IntakeResult)
def intake(req: IntakeRequest):
    # 동기 함수라 FastAPI가 스레드풀에서 실행한다 (이벤트 루프를 막지 않음)
    try:
        return run_intake(req.text)
    except Exception as exc:
        logger.exception("intake failed")
        return JSONResponse(status_code=502, content=error_info(exc))
