"""
이 파일의 역할: 그래프의 State(노드들이 함께 읽고 쓰는 공유 데이터)를 정의한다.

각 노드는 State를 받아서, 바꾸고 싶은 값만 dict로 돌려준다.
체크포인터가 저장하기 쉽도록 값은 pydantic 객체가 아니라 일반 dict/list로 넣는다.
"""

from typing_extensions import TypedDict


class LessonState(TypedDict, total=False):
    # --- 실행할 때 넣는 입력값 ---
    student_id: str  # 학생 프로필 파일 이름 (확장자 제외)
    unit_no: int | None  # 배울 과 번호. None이면 프로필의 next_unit을 쓴다
    book: str | None  # 교재 시리즈 (ko1, ko2). None이면 프로필의 next_book (기술 ADR-0032)
    lesson_minutes: int  # 수업 시간(분). 기본 50
    target_lang: str  # 설명 언어: "ja" 또는 "en"
    output_subdir: str  # (사용 안 함) PPT를 만들던 때의 저장 폴더. API 호환을 위해 남겨 둔다
    # profile을 입력값으로 넣으면 파일을 읽지 않고 그대로 쓴다 (API에서는 Spring이 넣어 준다, ADR-0005)

    # --- 로드 노드가 채우는 값 ---
    profile: dict  # 학생 프로필 (StudentProfile)
    textbook_unit: dict  # 이번에 배울 과 (단원 시트 UnitSheet, 칸 이름은 TextbookUnit과 같다)
    past_items: list[dict]  # 학생이 과거에 배운 교재 항목들 (복습용)

    # --- LLM 노드가 채우는 값 ---
    plan: dict  # 범주별 구성안 (LessonPlan)
    drafts: dict  # 범주별 결과 (범주 키 -> CategoryDraft)
    review_result: dict | None  # 자동 검토 결과 (checks: kind=code|llm, passed: 코드 점검 통과 여부)
    review_warning: bool  # 코드 점검(ID, 복습, 시간 합계)이 실패했으면 True
    briefing: dict  # 선생님 브리핑 (TeacherBriefing + references 출처 + slide_plan 15장 슬라이드 구성안)
    slides_fingerprint: str  # slide_plan을 만들 때의 4범주 초안 지문. 승인 때 초안이 달라졌으면 다시 만든다

    # --- 사람 검토 노드가 채우는 값 ---
    human_started: bool  # 선생님 검토가 한 번이라도 시작됐으면 True
    human_feedback: dict  # 범주 키 -> 선생님의 자연어 피드백
    approved_categories: list[str]  # 승인이 끝난 범주 키 목록
