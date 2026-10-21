"""
이 파일의 역할: ai-server API의 요청 모양과 SSE 이벤트 형식.

Spring(backend/aiclient)은 이 모양에 맞춰 요청을 보내고 이벤트를 읽는다.

SSE 이벤트 (event 이름 → data)
  started          {thread_id}
  node_finished    {thread_id, node, label}                 노드 하나가 끝날 때마다
  review_required  {thread_id, drafts, briefing, review_result, review_warning, approved_categories}
  done             {thread_id, pptx_file, pdf_file, render_ok, render_problems, plan, drafts, briefing}
  error            {thread_id, code, message, retryable}
"""

import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.agent.lesson_prep.schemas import StudentProfile

Category = Literal["review", "new_vocab", "new_grammar", "homework"]
SAFE_ID = r"^[A-Za-z0-9_-]{1,64}$"


class IntakeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000, description="선생님이 쓴 학생 설명")


class GrammarQaRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000, description="선생님의 문법 질문")
    native_language: Literal["ja", "en"] = "ja"
    student_level: int | None = Field(default=None, ge=0, le=6, description="학생의 표준 등급. 모르면 null")


class PrepStartRequest(BaseModel):
    thread_id: str = Field(pattern=SAFE_ID, description="Spring이 만든 수업 준비 thread ID")
    profile: StudentProfile
    book: str | None = Field(default=None, pattern=r"^[a-z0-9]+$", description="교재 시리즈 (ko1, ko2). 없으면 profile.next_book")
    unit_no: int | None = None
    lesson_minutes: int = Field(default=50, ge=10, le=180)
    target_lang: Literal["ja", "en"]
    # output/ 아래 저장 폴더. 경로 조작을 막으려고 "폴더/폴더" 모양의 상대 경로만 허용한다 (점·맨 앞 / 불가)
    output_subdir: str = Field(default="", max_length=128, pattern=r"^([A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*)?$")


class CategoryDecision(BaseModel):
    action: Literal["approve", "edit", "feedback"]
    explanation: str | None = None  # edit일 때 고친 설명 (없으면 기존 것 유지)
    script: str | None = None  # edit일 때 고친 대본 (없으면 기존 것 유지)
    feedback: str | None = None  # feedback일 때 필수

    @model_validator(mode="after")
    def feedback_needs_text(self):
        if self.action == "feedback" and not (self.feedback or "").strip():
            raise ValueError("action이 feedback이면 feedback 글이 있어야 합니다")
        return self


class PrepResumeRequest(BaseModel):
    decisions: dict[Category, CategoryDecision] = Field(min_length=1)


def sse(event: str, data: dict) -> str:
    """SSE 한 건을 글로 만든다. data는 한 줄 JSON으로 보낸다."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
