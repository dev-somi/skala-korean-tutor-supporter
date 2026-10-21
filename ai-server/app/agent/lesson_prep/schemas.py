"""
이 파일의 역할: 프로젝트에서 주고받는 데이터의 "모양"을 pydantic으로 정의한다.

- 교재 JSON (TextbookUnit)
- 학생 프로필 (StudentProfile)
- 수업 구성안 (LessonPlan)  -> plan_lesson 노드의 출력
- 개인화 설명 / 대본         -> 생성 노드의 출력
- 자동 검토 결과 (ReviewResult) -> auto_review 노드의 출력

pydantic을 쓰면 JSON 파일이나 LLM 출력의 형식이 틀렸을 때 바로 에러로 알려준다.
"""

from pydantic import BaseModel, Field

# 수업 자료의 4개 범주. 프로젝트 전체에서 이 이름(키)을 그대로 쓴다.
CATEGORIES = ["review", "new_vocab", "new_grammar", "homework"]

# 범주 키를 화면이나 PPT에 보여줄 때 쓰는 한국어 이름
CATEGORY_NAMES = {
    "review": "복습 내용",
    "new_vocab": "새로운 어휘",
    "new_grammar": "새로운 문법",
    "homework": "숙제 내용",
}


# ---------------------------------------------------------------------------
# 1. 교재 JSON
#    모든 항목에 바뀌지 않는 ID와 원문 페이지 번호(page)를 둔다.
# ---------------------------------------------------------------------------


class VocabItem(BaseModel):
    """어휘 한 개"""

    id: str  # 예: "u02-v01"
    word: str  # 단어 (한국어 원문)
    meaning: str  # 교재에 적힌 뜻
    pos: str  # 품사 (명사, 동사, 형용사, 표현 등)
    example: str = ""  # 교재에 실린 예문 (없으면 빈 문자열)
    page: int  # 교재 원문 페이지


class GrammarItem(BaseModel):
    """문법 한 개"""

    id: str  # 예: "u02-g01"
    form: str  # 문법 형태 (예: "-고 싶다")
    description: str  # 교재의 설명
    examples: list[str]  # 교재의 예문 (한국어 원문)
    page: int


class DialogueLine(BaseModel):
    """대화문의 한 줄"""

    speaker: str  # 말하는 사람
    text: str  # 대사


class Dialogue(BaseModel):
    """대화문 한 개"""

    id: str  # 예: "u02-d01"
    lines: list[DialogueLine]
    page: int


class Reading(BaseModel):
    """읽기 지문 한 개"""

    id: str  # 예: "u03-r01"
    text: str  # 지문 원문
    page: int


class Exercise(BaseModel):
    """연습문제 한 개"""

    id: str  # 예: "u02-e01"
    instruction: str  # 문제 지시문
    questions: list[str]  # 문제 목록. "[그림: ...]"은 교재의 그림을 글로 적어 둔 것
    page: int


class TextbookUnit(BaseModel):
    """교재의 한 과 전체"""

    unit_no: int  # 과 번호
    title: str  # 과 제목
    page_start: int  # 이 과가 시작하는 페이지
    page_end: int  # 이 과가 끝나는 페이지
    vocabulary: list[VocabItem]  # 목록의 순서 = 교재에서 제시하는 순서
    grammar: list[GrammarItem]
    dialogues: list[Dialogue]
    readings: list[Reading] = []  # 읽기 지문 (없는 과도 있어서 기본값은 빈 목록)
    exercises: list[Exercise]


# ---------------------------------------------------------------------------
# 2. 학생 프로필
# ---------------------------------------------------------------------------


class LessonRecord(BaseModel):
    """지난 수업 1회의 기록"""

    lesson_no: int  # 몇 번째 수업인지
    unit_no: int  # 그날 배운 과
    item_ids: list[str]  # 그날 배운 교재 항목 ID 목록


class StudentProfile(BaseModel):
    """학생 한 명의 프로필 (샘플은 가짜 데이터만 쓴다)"""

    student_id: str
    name: str
    native_language: str  # 모국어 (예: "ja", "en")
    level: str  # 한국어 수준 (예: "초급 1")
    goals: list[str]  # 학습 목표
    weaknesses: list[str]  # 약한 항목의 교재 ID 목록
    lesson_history: list[LessonRecord]  # 회차별로 배운 항목
    next_unit: int  # 다음에 배울 과 (선생님이 실행할 때 덮어쓸 수 있음)
    interests: list[str] = []  # 예문 개인화용 관심사 (드라마, 여행 …)
    weakness_notes: list[str] = []  # 교재 ID가 없는 약점의 자유 서술 ("받침 발음")
    notes: str = ""  # 선생님의 자유 메모
    standard_level: int | None = None  # 지금 배울 표준 등급 0~6 (기획 ADR-0018)
    target_level: int | None = None  # 목표 표준 등급 1~6
    persona: str | None = None  # 학습 목적 → 중심 교재 (기획 ADR-0016)


# ---------------------------------------------------------------------------
# 3. 수업 구성안 (plan_lesson 노드의 출력)
# ---------------------------------------------------------------------------


class CategoryPlan(BaseModel):
    """범주 하나의 구성안"""

    item_ids: list[str] = Field(description="이 범주에서 다룰 교재 항목 ID 목록")
    minutes: int = Field(description="이 범주에 배분한 시간(분)")
    reason: str = Field(description="이 항목들을 고른 이유 (한국어)")


class LessonPlan(BaseModel):
    """4개 범주의 구성안. 4개의 minutes 합계는 수업 시간과 같아야 한다."""

    review: CategoryPlan = Field(description="복습 내용: 과거에 배운 어휘/문법 + 약했던 부분")
    new_vocab: CategoryPlan = Field(description="새로운 어휘: 교재 제시 순서대로")
    new_grammar: CategoryPlan = Field(description="새로운 문법")
    homework: CategoryPlan = Field(description="숙제 내용: 교재 연습문제 등")


# ---------------------------------------------------------------------------
# 4. 개인화 설명과 대본 (생성 노드의 출력)
# ---------------------------------------------------------------------------


class ExampleSentence(BaseModel):
    """설명에 넣는 한국어 예문 한 개"""

    korean: str = Field(description="한국어 예문")
    is_new: bool = Field(description="교재에 없는, 새로 만든 예문이면 true")


class ExplanationOutput(BaseModel):
    """개인화 설명 생성 노드의 출력"""

    explanation: str = Field(description="학생에게 맞춘 설명 (대상 언어로 작성)")
    examples: list[ExampleSentence] = Field(description="설명에 쓴 한국어 예문 목록")


class ScriptOutput(BaseModel):
    """대본 생성 노드의 출력"""

    script: str = Field(description="선생님이 수업에서 말할 대본 (대상 언어로 작성)")


class CategoryDraft(BaseModel):
    """범주 하나의 최종 결과: 구성안 + 개인화 설명 + 대본"""

    item_ids: list[str]
    minutes: int
    reason: str
    explanation: str = ""
    examples: list[ExampleSentence] = []
    script: str = ""


# ---------------------------------------------------------------------------
# 4-1. 선생님 브리핑 (briefing 노드의 출력, 한국어로 작성)
# ---------------------------------------------------------------------------


class GrammarPoint(BaseModel):
    """이번 수업 문법 하나의 설명 포인트"""

    item_id: str = Field(description="교재 문법 항목 ID")
    key_points: list[str] = Field(description="수업에서 꼭 짚을 설명 포인트 2~4개")


class ExpectedQA(BaseModel):
    """학생이 할 법한 질문과 답"""

    question: str = Field(description="학생이 할 법한 질문")
    answer: str = Field(description="선생님이 할 수 있는 짧은 답")


# 브리핑은 작은 LLM 호출 3개로 나눠 만든다 (ADR-0013). 칸이 많으면 작은 모델이 칸끼리 내용을 섞는다.


class BriefingGrammar(BaseModel):
    """호출 1: 지침서 근거로 문법 설명 포인트"""

    grammar_points: list[GrammarPoint] = Field(description="이번 수업 문법별 핵심 설명 포인트")


class BriefingLearner(BaseModel):
    """호출 2: 모국어 화자가 틀리기 쉬운 점과 예상 질문"""

    common_mistakes: list[str] = Field(description="이 학생의 모국어 화자가 이번 문법에서 자주 틀리는 점 3~5개")
    expected_qa: list[ExpectedQA] = Field(description="학생이 이번 문법에 대해 할 법한 질문과 선생님의 짧은 답 3~4개")


class BriefingPersonal(BaseModel):
    """호출 3: 이 학생에게 맞춘 워밍업·활용 활동·팁"""

    warmup_questions: list[str] = Field(description="워밍업에서 학생에게 한국어로 물어볼 질문 2~3개")
    practice_activity: str = Field(description="활용 활동 1개: 상황, 학생 역할, 쓸 표현을 담은 롤플레이나 말하기 활동")
    tips: list[str] = Field(description="이 학생에게 맞춘 수업 팁 3개")


class CultureNote(BaseModel):
    """문화 후보 하나에 대한 정리 (후보 번호는 프롬프트의 번호)"""

    index: int = Field(description="문화 자료 후보 번호 (1부터)")
    summary: str = Field(description="선생님이 소개할 내용 1~2문장. 자료 원문에 있는 내용만. 문화와 관계없는 자료면 빈 문자열")
    question_ko: str = Field(description="학생 나라와 비교하는 쉬운 한국어 질문 1개 (학생 나라에 대해 단정하지 않고 묻는다)")
    question_l1: str = Field(description="같은 질문을 학생 모국어로")


class BriefingCulture(BaseModel):
    """호출 4: 세종학당 자료에서 찾은 문화 후보를 정리하고 비교 질문을 만든다 (기획 ADR-0023)"""

    notes: list[CultureNote] = Field(description="후보마다 하나씩")


class TeacherBriefing(BriefingGrammar, BriefingLearner, BriefingPersonal):
    """
    선생님이 수업 전에 읽는 브리핑 = 세 호출 결과를 합친 것.
    근거 자료의 출처(references)와 7단계 수업 틀(lesson_frame)은 briefing 노드가 코드로 덧붙인다.
    """


# ---------------------------------------------------------------------------
# 5. 자동 검토 결과 (auto_review 노드의 출력)
# ---------------------------------------------------------------------------


class CheckItem(BaseModel):
    """체크리스트 한 줄의 결과"""

    name: str = Field(description="점검 항목 이름")
    passed: bool = Field(description="통과하면 true, 실패하면 false")
    reason: str = Field(description="그렇게 판단한 이유 (한국어)")


class ReviewResult(BaseModel):
    """체크리스트 전체 결과"""

    checks: list[CheckItem]
