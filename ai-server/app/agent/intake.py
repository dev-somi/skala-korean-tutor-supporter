"""
이 파일의 역할: 학생 등록(student_intake). 선생님의 자연어 설명 → 학생 카드 초안.

흐름: 구조화 추출(저가 모델) → 코드 검증(권위 게이트) → 초안 + 경고를 돌려준다.
저장은 하지 않는다. 선생님이 확인한 뒤 Spring이 저장한다 (PRD 8-3, ADR-0005).
분기·루프가 없어서 그래프 대신 함수 두 개로 둔다.
"""

from langsmith import traceable
from pydantic import BaseModel, Field

from app.agent.lesson_prep import llm
from app.agent.lesson_prep.textbook import load_all_items

SUPPORTED_LANGS = ("ja", "en")  # shared/constraints.json 의 native_languages 와 같아야 한다
# shared/constraints.json 의 personas 와 같아야 한다 (기획 ADR-0016, ADR-0018)
PERSONAS = ("structured", "conversation", "travel", "business")
STANDARD_LEVELS = range(0, 7)  # 0 = 입문, 1~6 = 표준 N급


class WeaknessDraft(BaseModel):
    item_id: str | None = Field(default=None, description="관련 교재 항목 ID. 목록에 맞는 것이 없으면 null")
    description: str = Field(description="약점의 자유 서술 (한국어)")


class StudentDraft(BaseModel):
    """LLM이 채우는 학생 카드 초안. 설명에 없는 칸은 비워 둔다(null 또는 빈 목록)."""

    name: str | None = Field(default=None, description="학생 이름(가명)")
    native_language: str | None = Field(default=None, description='모국어 코드. "ja" 또는 "en". 모르면 null')
    level: str | None = Field(default=None, description="수준 세부 메모를 한국어로 짧게 (예: '한글 읽기 가능, 받침 발음 약함')")
    standard_level: int | None = Field(
        default=None, description="지금 배울 표준 등급. 0=입문(한글 못 읽음), 1~6=N급. 메모에 등급이나 레벨테스트 결과가 분명히 있을 때만, 아니면 null"
    )
    target_level: int | None = Field(default=None, description="목표 등급 1~6. 메모에 목표 급수가 분명히 있을 때만 (예: 'TOPIK 3급 따고 싶대' → 3), 아니면 null")
    persona: str | None = Field(
        default=None,
        description='학습 목적 추천: "structured"(체계적 학습·시험), "conversation"(일상 회화·드라마), "travel"(여행), "business"(업무). 목표를 보고 고른다. 알 수 없으면 null',
    )
    goals: list[str] = Field(default=[], description="학생이 말한 학습 목표")
    interests: list[str] = Field(default=[], description="관심사 (예문 개인화용)")
    weaknesses: list[WeaknessDraft] = Field(default=[], description="약점 목록")
    next_unit: int | None = Field(default=None, description="다음에 배울 과 번호. 언급이 없으면 null")
    lesson_minutes_default: int | None = Field(default=None, description="수업 시간(분). 언급이 없으면 null")
    notes: str = Field(default="", description="위 칸에 들어가지 않는 나머지 정보 (성격, 수업 스타일, 일정 등)")


class IntakeResult(BaseModel):
    draft: StudentDraft
    warnings: list[str]


def textbook_catalog(items: dict) -> str:
    """
    프롬프트에 넣을 문법 목록 (ID와 한 줄 요약). 약점은 대부분 문법이라 문법만 넣는다.
    단원 시트가 생기면서 어휘까지 넣으면 수백 줄이 되어 작은 모델이 ID를 잘못 고른다 (기술 ADR-0032).
    """
    lines = []
    for item_id, item in items.items():
        if item["kind"] == "grammar":
            lines.append(f"[{item_id}] 문법: {item['form']} ({item['book']} {item['unit_no']}과)")
    return "\n".join(lines)


@traceable(run_type="tool")
def validate_draft(draft: dict, items: dict) -> IntakeResult:
    """
    권위 게이트: LLM이 채운 값을 코드가 다시 검사한다.
    - 모국어가 지원 값(ja/en)이 아니면 비우고 경고
    - 교재에 없는 항목 ID는 지우고(설명은 남김) 경고
    - 과 번호가 교재에 없으면 비우고 경고
    """
    warnings = []
    draft = dict(draft)

    if draft.get("native_language") not in SUPPORTED_LANGS:
        if draft.get("native_language"):
            warnings.append(f"지원하지 않는 모국어 값 '{draft['native_language']}'을 비웠습니다. ja 또는 en으로 골라 주세요.")
        else:
            warnings.append("모국어를 알 수 없습니다. 직접 골라 주세요.")
        draft["native_language"] = None

    weaknesses = []
    for weakness in draft.get("weaknesses", []):
        weakness = dict(weakness)
        if weakness.get("item_id") and weakness["item_id"] not in items:
            warnings.append(f"교재에 없는 항목 ID '{weakness['item_id']}'를 지웠습니다 (약점: {weakness['description']}).")
            weakness["item_id"] = None
        weaknesses.append(weakness)
    draft["weaknesses"] = weaknesses

    for key, allowed, name in [("standard_level", STANDARD_LEVELS, "현재 수준"), ("target_level", range(1, 7), "목표 수준")]:
        if draft.get(key) is not None and draft[key] not in allowed:
            warnings.append(f"{name} 값 {draft[key]}은 등급 범위 밖이라 비웠습니다.")
            draft[key] = None
    # 현재 수준은 필수다. 메모에 없으면 AI가 짐작하지 않는다 (기획 ADR-0018)
    if draft.get("standard_level") is None:
        warnings.append("현재 수준을 알 수 없습니다. 체험수업 레벨테스트 결과로 골라 주세요.")

    if draft.get("persona") is not None and draft["persona"] not in PERSONAS:
        warnings.append(f"알 수 없는 학습 목적 '{draft['persona']}'을 비웠습니다.")
        draft["persona"] = None

    units = {item["unit_no"] for item in items.values()}
    if draft.get("next_unit") is not None and draft["next_unit"] not in units:
        warnings.append(f"교재 데이터에 없는 과 번호 {draft['next_unit']}를 비웠습니다.")
        draft["next_unit"] = None

    return IntakeResult(draft=StudentDraft.model_validate(draft), warnings=warnings)


@traceable(name="student_intake")
def run_intake(text: str) -> IntakeResult:
    """자연어 설명 → 검증된 학생 카드 초안"""
    items = load_all_items()
    raw = llm.call_llm("student_intake", StudentDraft, {"text": text, "catalog": textbook_catalog(items)}, tier="fast")
    return validate_draft(raw, items)
