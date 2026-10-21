"""
이 파일의 역할: 학습자별 진도·향상 리포트 API (기획 ADR-0019, 기술 ADR-0018).

  POST /report/progress   Spring이 모은 승인 기록·약점 → 리포트 (숫자 + 학생에게 보낼 문장 초안)

저장하지 않는다. 선생님이 화면에서 문장을 고쳐 복사해 보낸다.
"""

from fastapi import APIRouter

from app.standard.report import ReportRequest, build_report

router = APIRouter(tags=["report"])


@router.post("/report/progress")
def progress_report(req: ReportRequest) -> dict:
    return build_report(req)
