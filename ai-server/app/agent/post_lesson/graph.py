"""
이 파일의 역할: 수업 후 기록 그래프 (post_lesson).

  START -> extract -> gate -> write_feedback -> validate -(합격 또는 재작성 한도 초과)-> END
                                    ^                |
                                    └──(불합격)───────┘   (재작성 최대 MAX_FEEDBACK_REWRITE회)

  extract        (LLM)  메모 → 다룬 항목, 잘한 점, 오류, 약점 변경안, 숙제, 다음 수업 메모
  gate           (코드) 권위 게이트: 없는 교재 ID·없는 약점 해결·중복 약점 추가를 지우고 경고를 남긴다
  write_feedback (LLM)  학생에게 보낼 피드백 메시지 (학생 언어 + 한국어 번역)
  validate       (LLM, 저가 모델) 관련성 / 완전성 / 명확성 / 학습자 수준 적합성

HITL은 그래프 밖에서 한다: 결과는 "미처리 기록"으로 저장되고, 선생님이 항목별로 승인하면 Spring이 반영한다.
그래서 interrupt와 checkpointer가 필요 없다.
"""

import json

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.agent.lesson_prep import llm
from app.agent.lesson_prep.textbook import format_item_for_prompt, load_all_items
from app.agent.post_lesson.schemas import FeedbackMessage, FeedbackValidation, RecordExtraction

MAX_FEEDBACK_REWRITE = 2  # Validator 불합격 시 피드백 메시지를 다시 쓰는 최대 횟수


class PostLessonState(TypedDict, total=False):
    # 입력
    profile: dict
    lesson: dict
    raw_note: str
    current_weaknesses: list[dict]
    # 노드가 채우는 값
    extraction: dict
    warnings: list[str]
    feedback_message: dict
    validation: dict
    rewrite_count: int


def to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def lesson_items_text(lesson: dict, items: dict) -> str:
    """이번 수업 과의 교재 항목 + 구성안에 있던 항목(복습 포함)을 프롬프트용 글로."""
    ids = [i for i, item in items.items() if item["unit_no"] == lesson["unit_no"]]
    for category in (lesson.get("plan") or {}).values():
        ids.extend(i for i in category.get("item_ids", []) if i not in ids)
    return "\n".join(format_item_for_prompt(items[i]) for i in ids if i in items) or "(없음)"


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------


def extract(state: dict) -> dict:
    items = load_all_items()
    values = {
        "profile": to_json(state["profile"]),
        "lesson": to_json({k: v for k, v in state["lesson"].items() if k != "plan"}),
        "plan": to_json(state["lesson"].get("plan")) if state["lesson"].get("plan") else "(수업 준비 기록 없음)",
        "current_weaknesses": to_json(state.get("current_weaknesses", [])) if state.get("current_weaknesses") else "(없음)",
        "items": lesson_items_text(state["lesson"], items),
        "raw_note": state["raw_note"],
    }
    return {"extraction": llm.call_llm("extract_record", RecordExtraction, values)}


def gate(state: dict) -> dict:
    """권위 게이트 (참고노트 4-1): LLM이 만든 ID와 약점 변경을 코드가 다시 검사해서 고친다."""
    items = load_all_items()
    current = {w["id"]: w for w in state.get("current_weaknesses", [])}
    ex = json.loads(json.dumps(state["extraction"]))  # 깊은 복사
    warnings = []

    def check_id(item_id, where):
        if item_id and item_id not in items:
            warnings.append(f"{where}: 교재에 없는 항목 ID '{item_id}'를 지웠습니다.")
            return None
        return item_id

    covered = []
    for item_id in ex["covered_item_ids"]:
        if check_id(item_id, "다룬 항목") and item_id not in covered:
            covered.append(item_id)
    ex["covered_item_ids"] = covered

    for error in ex["errors"]:
        error["item_id"] = check_id(error.get("item_id"), f"오류 '{error['student_said']}'")
    for hw in ex["homework"]:
        hw["item_id"] = check_id(hw.get("item_id"), f"숙제 '{hw['description']}'")

    changes = []
    active_ids = {w["item_id"] for w in current.values() if w.get("item_id")}
    active_desc = {w["description"].strip() for w in current.values()}
    for change in ex["weakness_changes"]:
        change["item_id"] = check_id(change.get("item_id"), f"약점 '{change['description']}'")
        if change["action"] == "resolve":
            target = current.get(change.get("weakness_id"))
            if target is None and change["item_id"]:
                # id를 못 맞췄으면 같은 교재 ID의 현재 약점을 찾아 준다
                target = next((w for w in current.values() if w.get("item_id") == change["item_id"]), None)
            if target is None:
                warnings.append(f"현재 약점 목록에 없는 약점 해결 제안을 지웠습니다: {change['description']}")
                continue
            change["weakness_id"] = target["id"]
            change["item_id"] = target.get("item_id")
            change["description"] = target["description"]
        else:
            change["weakness_id"] = None
            if (change["item_id"] and change["item_id"] in active_ids) or change["description"].strip() in active_desc:
                warnings.append(f"이미 있는 약점이라 추가 제안을 지웠습니다: {change['description']}")
                continue
        changes.append(change)
    ex["weakness_changes"] = changes

    return {"extraction": ex, "warnings": warnings}


def write_feedback(state: dict) -> dict:
    lang = state["lesson"]["target_lang"]
    previous = state.get("feedback_message")
    validation = state.get("validation")
    values = {
        "lang_name": llm.LANG_NAMES[lang],
        "profile": to_json(state["profile"]),
        "extraction": to_json(state["extraction"]),
        "previous_message": previous["target_lang_text"] if previous else "(없음)",
        "validator_feedback": validation["reasoning"] if validation and not validation["is_acceptable"] else "(없음)",
    }
    message = llm.call_llm("write_feedback", FeedbackMessage, values)
    rewrite_count = state.get("rewrite_count", 0) + (1 if previous else 0)
    return {"feedback_message": message, "rewrite_count": rewrite_count}


def validate(state: dict) -> dict:
    values = {
        "lang_name": llm.LANG_NAMES[state["lesson"]["target_lang"]],
        "level": state["profile"]["level"],
        "extraction": to_json(state["extraction"]),
        "message": to_json(state["feedback_message"]),
    }
    return {"validation": llm.call_llm("validate_feedback", FeedbackValidation, values, tier="fast")}


def route_after_validate(state: dict) -> str:
    if state["validation"]["is_acceptable"] or state.get("rewrite_count", 0) >= MAX_FEEDBACK_REWRITE:
        return END
    return "write_feedback"


def build_graph():
    builder = StateGraph(PostLessonState)
    builder.add_node("extract", extract)
    builder.add_node("gate", gate)
    builder.add_node("write_feedback", write_feedback)
    builder.add_node("validate", validate)
    builder.add_edge(START, "extract")
    builder.add_edge("extract", "gate")
    builder.add_edge("gate", "write_feedback")
    builder.add_edge("write_feedback", "validate")
    builder.add_conditional_edges("validate", route_after_validate, ["write_feedback", END])
    return builder.compile()


def make_initial_state(req) -> dict:
    return {
        "profile": req.profile.model_dump(),
        "lesson": req.lesson.model_dump(),
        "raw_note": req.raw_note,
        "current_weaknesses": [w.model_dump() for w in req.current_weaknesses],
        "warnings": [],
        "rewrite_count": 0,
    }
