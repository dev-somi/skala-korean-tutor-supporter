"""
이 파일의 역할: 그래프의 분기(완료 기준)를 가짜 LLM으로 테스트한다.

  - 끝까지 실행하면 .pptx가 만들어진다
  - auto_review는 다시 만들지 않는다: LLM 점검 실패는 참고 의견, 코드 점검 실패는 경고
  - 구성안은 코드 규칙이라 시간 합계가 항상 수업 시간과 같다
  - 한 범주에만 피드백을 주면 그 범주만 다시 만들어진다
  - 직접 수정한 내용이 최종 수업안에 그대로 들어간다
  - 모두 승인하면 PPT 없이 끝나고, 브리핑에 7단계 수업 틀이 들어 있다

실행 방법: uv run pytest
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agent.lesson_prep import nodes
from app.agent.lesson_prep.graph import build_graph, make_initial_state
from app.agent.lesson_prep.schemas import CATEGORIES

CONFIG = {"configurable": {"thread_id": "test"}}
APPROVE_ALL = {category: {"action": "approve"} for category in CATEGORIES}


def start(fake_llm):
    """그래프를 처음부터 실행해서 선생님 검토에서 멈춘 상태로 만든다."""
    graph = build_graph(InMemorySaver())
    result = graph.invoke(make_initial_state("student_sample"), CONFIG)
    return graph, result


def test_end_to_end_ends_with_lesson_frame(fake_llm):
    """자동 검토 통과 -> 모두 승인 -> 끝. PPT는 만들지 않고, 브리핑에 50분짜리 7단계 수업 틀이 있다."""
    graph, result = start(fake_llm)
    payload = result["__interrupt__"][0].value  # human_review에서 멈춤
    assert payload["review_warning"] is False
    assert payload["briefing"]["lesson_frame"]  # 검토 화면에서도 틀이 보인다

    result = graph.invoke(Command(resume=APPROVE_ALL), CONFIG)

    assert "__interrupt__" not in result
    assert "pptx_path" not in result
    for category in CATEGORIES:
        assert result["drafts"][category]["explanation"]
        assert result["drafts"][category]["script"]
    assert sum(step["minutes"] for step in result["briefing"]["lesson_frame"]) == 50


def test_llm_review_fail_is_advice_only(fake_llm):
    """LLM 점검이 실패해도 다시 만들지 않고, 참고 의견으로 붙여 바로 선생님에게 넘긴다 (ADR-0021)."""
    fake_llm.review_fail_times = 99
    graph, result = start(fake_llm)

    assert fake_llm.count("auto_review") == 1
    assert fake_llm.count("write_explanation") == 4  # 범주 4개 x 1번
    payload = result["__interrupt__"][0].value
    assert payload["review_warning"] is False  # 코드 점검은 통과
    assert payload["review_result"]["passed"] is True
    llm_checks = [c for c in payload["review_result"]["checks"] if c["kind"] == "llm"]
    assert llm_checks and not llm_checks[0]["passed"]


def test_code_check_fail_warns_without_retry(fake_llm, monkeypatch):
    """코드 점검이 실패하면 경고를 달아 넘긴다. 구성안은 코드 규칙이라 다시 만들어도 같으므로 재시도하지 않는다."""
    monkeypatch.setattr(nodes, "code_checks", lambda state: [{"name": "시간 합계", "passed": False, "reason": "가짜"}])
    graph, result = start(fake_llm)

    assert fake_llm.count("auto_review") == 1
    payload = result["__interrupt__"][0].value
    assert payload["review_warning"] is True
    assert payload["review_result"]["passed"] is False


def test_plan_fits_any_lesson_minutes(fake_llm):
    """구성안은 코드 규칙이라 수업 시간이 바뀌어도 코드 점검(ID, 복습, 시간 합계)을 모두 통과한다."""
    graph = build_graph(InMemorySaver())
    result = graph.invoke(make_initial_state("student_sample", lesson_minutes=40), CONFIG)

    payload = result["__interrupt__"][0].value
    assert all(check["passed"] for check in payload["review_result"]["checks"])
    assert sum(step["minutes"] for step in payload["briefing"]["lesson_frame"]) == 40


def test_feedback_regenerates_only_that_category(fake_llm):
    """숙제에만 피드백을 주면 숙제만 다시 만들어지고, 나머지 3개는 그대로다."""
    graph, result = start(fake_llm)
    before = result["__interrupt__"][0].value["drafts"]

    decisions = dict(APPROVE_ALL)
    decisions["homework"] = {"action": "feedback", "feedback": "숙제를 더 짧게 해 주세요"}
    result = graph.invoke(Command(resume=decisions), CONFIG)

    # 다시 선생님 검토에서 멈춘다 (자동 검토는 다시 하지 않는다)
    payload = result["__interrupt__"][0].value
    after = payload["drafts"]
    assert fake_llm.count("auto_review") == 1
    assert payload["approved_categories"] == ["review", "new_vocab", "new_grammar"]

    for category in ["review", "new_vocab", "new_grammar"]:
        assert after[category] == before[category]  # 그대로
    assert after["homework"]["explanation"] != before["homework"]["explanation"]  # 바뀜
    assert after["homework"]["script"] != before["homework"]["script"]

    # 다시 만들 때 이전 초안과 피드백이 프롬프트에 함께 전달된다
    name, values = fake_llm.calls[-2]  # 마지막 설명 생성 호출
    assert name == "write_explanation"
    assert values["feedback"] == "숙제를 더 짧게 해 주세요"
    assert values["previous_draft"] == before["homework"]["explanation"]

    # 남은 숙제를 승인하면 끝난다
    result = graph.invoke(Command(resume={"homework": {"action": "approve"}}), CONFIG)
    assert "__interrupt__" not in result


def test_edit_goes_into_final_plan_as_is(fake_llm):
    """직접 수정한 설명과 대본이 글자 하나 바뀌지 않고 최종 수업안에 들어간다."""
    graph, result = start(fake_llm)

    decisions = dict(APPROVE_ALL)
    decisions["new_grammar"] = {
        "action": "edit",
        "explanation": "先生が直接書いた説明です。",
        "script": "先生が直接書いた台本です。",
    }
    result = graph.invoke(Command(resume=decisions), CONFIG)

    # 수정한 범주는 LLM을 다시 부르지 않는다 (범주 4개 x 처음 1번씩만)
    assert fake_llm.count("write_explanation") == 4
    assert result["drafts"]["new_grammar"]["explanation"] == "先生が直接書いた説明です。"
    assert result["drafts"]["new_grammar"]["script"] == "先生が直接書いた台本です。"


def test_culture_point_from_materials(fake_llm):
    """문화는 세종학당 자료 후보에서 오고, 문화 내용이 아닌 후보는 빠지며, 도입 단계가 1순위를 가리킨다 (기획 ADR-0023)."""
    graph, result = start(fake_llm)
    briefing = result["__interrupt__"][0].value["briefing"]

    assert [c["source"] for c in briefing["culture"]] == ["세종한국문화 1 1과 「문화」 22~23쪽"]  # 2번은 요약이 비어 빠짐
    assert briefing["culture"][0]["question_l1"] == "日本でも一緒に歌いますか？"
    present = next(s for s in briefing["lesson_frame"] if s["key"] == "present")
    assert present["culture"] == 0


def test_no_culture_found_keeps_preparing(fake_llm, monkeypatch):
    """자료에서 문화 후보를 못 찾아도 수업 준비는 끝나고, 화면이 선생님에게 채워 달라고 할 수 있게 비워 둔다."""
    monkeypatch.setattr(nodes, "collect_culture", lambda unit: [])
    graph, result = start(fake_llm)
    briefing = result["__interrupt__"][0].value["briefing"]

    assert fake_llm.count("briefing_culture") == 0
    assert briefing["culture"] == []
    assert next(s for s in briefing["lesson_frame"] if s["key"] == "present")["culture"] is None
