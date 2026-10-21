"""
이 파일의 역할: 노드 함수들을 LangGraph 그래프로 연결한다.

흐름
  START -> load_profile -> load_textbook -> plan_lesson -> write_explanations -> write_scripts
        -> auto_review -> briefing -> write_slides -> human_review
           (auto_review는 다시 만들지 않는다. 코드 점검 실패는 경고, LLM 점검은 참고 의견, ADR-0021)
  human_review -(모두 승인, 초안이 slide_plan을 만든 뒤 그대로)-> END   (PPT는 만들지 않는다. 결과는 15장 슬라이드 구성안, 기술 ADR-0034)
               -(모두 승인, 초안이 달라짐)-> write_slides -> END
               -(피드백 있음)-> write_explanations -> write_scripts -> human_review
"""

from langgraph.graph import END, START, StateGraph

from app.agent.lesson_prep import lesson_frame, nodes
from app.agent.lesson_prep.schemas import CATEGORIES
from app.agent.lesson_prep.state import LessonState

# ---------------------------------------------------------------------------
# 분기 함수: State를 보고 "다음에 갈 노드 이름"을 돌려준다
# ---------------------------------------------------------------------------


def route_after_scripts(state: dict) -> str:
    """대본을 만든 뒤: 처음 만든 것이면 자동 검토로, 선생님 피드백으로 다시 만든 것이면 선생님에게."""
    if state.get("human_started"):
        return "human_review"
    return "auto_review"


def route_after_human_review(state: dict) -> str:
    """선생님 검토 뒤: 4개 범주가 모두 승인됐으면 끝(슬라이드가 낡았으면 한 번 더 만들고), 아니면 남은 범주를 다시 생성."""
    if len(state["approved_categories"]) == len(CATEGORIES):
        if state.get("slides_fingerprint") != lesson_frame.drafts_fingerprint(state["drafts"]):
            return "write_slides"
        return END
    return "write_explanations"


def route_after_slides(state: dict) -> str:
    """슬라이드를 만든 뒤: 이미 모두 승인된 상태에서 다시 만든 것이면 끝, 처음 만든 것이면 선생님에게."""
    if len(state.get("approved_categories", [])) == len(CATEGORIES):
        return END
    return "human_review"


# ---------------------------------------------------------------------------
# 그래프 만들기
# ---------------------------------------------------------------------------


def build_graph(checkpointer):
    """
    그래프를 만들어 돌려준다.
    checkpointer: 진행 상황을 저장하는 도구. human_review에서 멈췄다가 재개하려면 꼭 필요하다.
    """
    builder = StateGraph(LessonState)

    # 1) 노드 등록 (이름, 함수)
    builder.add_node("load_profile", nodes.load_profile)
    builder.add_node("load_textbook", nodes.load_textbook)
    builder.add_node("plan_lesson", nodes.plan_lesson)
    builder.add_node("write_explanations", nodes.write_explanations)
    builder.add_node("write_scripts", nodes.write_scripts)
    builder.add_node("auto_review", nodes.auto_review)
    builder.add_node("briefing", nodes.briefing)
    builder.add_node("write_slides", nodes.write_slides)
    builder.add_node("human_review", nodes.human_review)

    # 2) 항상 같은 순서로 가는 연결
    builder.add_edge(START, "load_profile")
    builder.add_edge("load_profile", "load_textbook")
    builder.add_edge("load_textbook", "plan_lesson")
    builder.add_edge("plan_lesson", "write_explanations")
    builder.add_edge("write_explanations", "write_scripts")
    builder.add_edge("auto_review", "briefing")
    builder.add_edge("briefing", "write_slides")

    # 3) 조건에 따라 갈라지는 연결 (분기 함수, 갈 수 있는 노드 목록)
    builder.add_conditional_edges("write_scripts", route_after_scripts, ["auto_review", "human_review"])
    builder.add_conditional_edges("write_slides", route_after_slides, [END, "human_review"])
    builder.add_conditional_edges("human_review", route_after_human_review, [END, "write_explanations", "write_slides"])

    return builder.compile(checkpointer=checkpointer)


def make_initial_state(
    student_id: str,
    unit_no: int | None = None,
    target_lang: str = "ja",
    lesson_minutes: int = 50,
    profile: dict | None = None,
    output_subdir: str = "",
    book: str | None = None,
) -> dict:
    """
    그래프를 처음 실행할 때 넣는 State를 만든다. 이전 실행의 값이 남지 않도록 모두 초기화한다.
    profile을 주면 파일 대신 그것을 쓴다.
    """
    return {
        "profile": profile or {},
        "output_subdir": output_subdir,
        "briefing": {},
        "student_id": student_id,
        "unit_no": unit_no,
        "book": book,
        "lesson_minutes": lesson_minutes,
        "target_lang": target_lang,
        "drafts": {},
        "review_result": None,
        "review_warning": False,
        "human_started": False,
        "human_feedback": {},
        "approved_categories": [],
        "slides_fingerprint": "",
    }
