"""
이 파일의 역할: 체험수업 레벨테스트 API (기획 ADR-0018, 기술 ADR-0017).

  GET  /level-test         문항 (표준 항목으로 채운 것)
  POST /level-test/score   {answers: {문항 ID: true|false}} → 추천 등급

추천만 한다. 학생 수준은 선생님이 학생 등록 화면에서 골라 저장한다.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.standard.level_test import ScoreResult, load_level_test, score

router = APIRouter(tags=["level-test"])


class ScoreRequest(BaseModel):
    answers: dict[str, bool] = Field(description="확인한 문항만. 맞으면 true, 틀리면 false")


def known_ids() -> set[str]:
    test = load_level_test()
    ids = {w["id"] for w in test["hangul"]["words"]}
    for section in test["levels"]:
        ids |= {g["id"] for g in section["grammar"]} | {v["id"] for v in section["vocab"]}
    return ids


@router.get("/level-test")
def get_level_test() -> dict:
    return load_level_test()


@router.post("/level-test/score", response_model=ScoreResult)
def post_score(req: ScoreRequest):
    unknown = sorted(set(req.answers) - known_ids())
    if unknown:
        raise HTTPException(status_code=422, detail=f"없는 문항 ID: {', '.join(unknown)}")
    return score(req.answers)
