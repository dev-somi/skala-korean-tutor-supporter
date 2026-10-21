"""
이 파일의 역할: 수업 후 기록(post_lesson)에서 주고받는 데이터의 모양.
PRD 7장 LessonRecord 의 AI 초안 부분. 반영(DB 쓰기)은 선생님이 승인한 뒤 Spring이 한다.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.agent.lesson_prep.schemas import StudentProfile


class CurrentWeakness(BaseModel):
    """학생의 지금 약점 (Spring DB의 weakness 행)"""

    id: int
    item_id: str | None = None
    description: str


class LessonInfo(BaseModel):
    lesson_no: int
    unit_no: int
    minutes: int
    target_lang: Literal["ja", "en"]
    plan: dict | None = None  # 수업 준비 때 확정한 구성안 (없으면 null)


class LessonError(BaseModel):
    student_said: str = Field(description="학생이 실제로 말한(쓴) 틀린 표현. 메모에 없으면 틀린 내용을 짧게 요약")
    correction: str = Field(description="바른 표현")
    item_id: str | None = Field(default=None, description="관련 교재 항목 ID. 없으면 null")
    note: str = Field(default="", description="선생님 참고 메모 (한국어)")


class WeaknessChange(BaseModel):
    action: Literal["add", "resolve"] = Field(description="add = 새 약점, resolve = 기존 약점 해결")
    weakness_id: int | None = Field(default=None, description="resolve일 때 해결한 '현재 약점'의 id. add면 null")
    item_id: str | None = Field(default=None, description="관련 교재 항목 ID. 없으면 null")
    description: str = Field(description="약점 설명 (한국어)")


class HomeworkItem(BaseModel):
    item_id: str | None = Field(default=None, description="교재 연습문제 등 항목 ID. 없으면 null")
    description: str = Field(description="숙제 내용 (한국어)")


class RecordExtraction(BaseModel):
    """수업 메모에서 뽑아낸 구조화 기록"""

    covered_item_ids: list[str] = Field(description="이번 수업에서 실제로 다룬 교재 항목 ID")
    strengths: list[str] = Field(description="잘한 점 (한국어)")
    errors: list[LessonError] = Field(description="틀린 점과 교정")
    weakness_changes: list[WeaknessChange] = Field(description="약점 추가·해결 제안")
    homework: list[HomeworkItem] = Field(description="숙제")
    next_lesson_note: str = Field(description="다음 수업에서 할 것 (한국어). 없으면 빈 문자열")


# 학생 반응 장면의 종류 (기획 ADR-0029, 기술 ADR-0033). 점수는 graph.judge가 코드로 매긴다
EpisodeKind = Literal["error", "asked_again", "hesitation", "re_explained", "self_corrected", "correct"]


class Episode(BaseModel):
    item_id: str = Field(description="이 장면과 관련된 교재 항목 ID. 아래 '다룬 항목' 목록에 있는 ID만")
    kind: EpisodeKind = Field(
        description="error=학생이 틀림, asked_again=학생이 같은 것을 다시 물어봄, hesitation=망설이거나 모르겠다고 함, "
        "re_explained=선생님이 같은 것을 다시 설명함, self_corrected=학생이 스스로 고침, correct=학생이 바로 맞힘"
    )
    quote: str = Field(description="그 장면의 원문 한 줄을 메모·녹취록에서 그대로 복사 (고치거나 요약하지 않음)")


class Observation(BaseModel):
    """다룬 항목별 학생 반응 장면 (observe 노드 출력)"""

    episodes: list[Episode] = Field(description="찾은 장면 목록. 없으면 빈 목록")


class FeedbackMessage(BaseModel):
    target_lang_text: str = Field(description="학생에게 보낼 메시지 (학생 언어)")
    korean_text: str = Field(description="위 메시지의 한국어 번역 (선생님 확인용)")


class FeedbackValidation(BaseModel):
    """Validator(LLM-as-Judge) 결과. 4개 기준을 한 번에 본다 (참고노트 4-3)."""

    is_acceptable: bool = Field(description="4개 기준을 모두 만족하면 true")
    reasoning: str = Field(description="판단 이유. 불합격이면 무엇을 고칠지 구체적으로 (한국어)")


class PostLessonRequest(BaseModel):
    profile: StudentProfile
    lesson: LessonInfo
    raw_note: str = Field(min_length=1, max_length=30000)  # 50분 녹취록 전체 (기획 ADR-0029)
    current_weaknesses: list[CurrentWeakness] = []
