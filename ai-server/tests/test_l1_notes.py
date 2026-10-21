"""
이 파일의 역할: 모국어별 지식 데이터(l1_notes.json)와 찾기 규칙, 브리핑 연결을 테스트한다. (기술 ADR-0022)

실행 방법: uv run pytest
"""

import json

from langgraph.checkpoint.memory import InMemorySaver

from app.agent.lesson_prep.graph import build_graph, make_initial_state
from app.agent.lesson_prep.textbook import get_data_dir
from app.standard import l1_notes
from app.standard.levels import _textbook_map, get_item

NOTES = json.loads((get_data_dir() / "standard" / "l1_notes.json").read_text(encoding="utf-8"))["notes"]
CONFIG = {"configurable": {"thread_id": "l1"}}


def test_notes_point_to_real_standard_items_and_have_both_languages():
    """노트의 표준 ID가 실제로 있고, 일본어·영어 모두 필요한 칸이 있다."""
    for note in NOTES:
        assert note["std_ids"] and all(get_item(i) for i in note["std_ids"]), note["form"]
        for lang in ("ja", "en"):
            body = note[lang]
            assert isinstance(body["reviewed"], bool)
            assert body["common_mistakes"] and body["expected_qa"] and body["explain_tip"]
            assert all(qa["question"] != qa["answer"] for qa in body["expected_qa"])


def test_every_mapped_textbook_grammar_has_a_note():
    """대응표에 있는 교재 문법(지금은 한국어 1의 2~4과)은 모두 노트가 있다. 새 과를 대응표에 넣으면 노트도 써야 한다."""
    for item_id in _textbook_map():
        if "-g" in item_id:
            assert l1_notes.notes_for_item(item_id), item_id


def test_lookup_dedupes_and_prefers_construction_note():
    # -습니다(std-g-030)와 -습니까(std-g-029)는 노트 하나
    found, missing = l1_notes.lookup(["u03-g01", "u03-g02", "u03-g03"], "ja")
    assert [n["form"] for n in found] == ["-습니다/-습니까", "을/를", "도"]
    assert missing == []
    # 이/가 아니다는 "이/가" 노트까지 끌어오지 않는다
    found, _ = l1_notes.lookup(["u02-g02"], "en")
    assert [n["form"] for n in found] == ["이/가 아니다"]


def test_lookup_reports_missing_items():
    found, missing = l1_notes.lookup(["u99-g01"], "ja")
    assert found == [] and missing == ["u99-g01"]


def test_briefing_uses_notes_without_llm(fake_llm):
    """데이터에 모든 문법의 노트가 있으면 모국어 칸에 LLM을 부르지 않는다."""
    result = build_graph(InMemorySaver()).invoke(make_initial_state("student_sample"), CONFIG)
    briefing = result["__interrupt__"][0].value["briefing"]

    assert fake_llm.count("briefing_learner") == 0
    assert any("ドラマが好き" in m for m in briefing["common_mistakes"])  # 을/를 노트의 내용
    assert {s["origin"] for s in briefing["l1_sources"]} == {"draft"}  # 아직 검수 전
    assert any(t.startswith("[을/를]") for t in briefing["tips"])


def test_briefing_falls_back_to_llm_for_missing(fake_llm, monkeypatch):
    """노트가 없는 문법만 LLM이 만들고, 출처를 llm으로 표시한다."""
    monkeypatch.setattr(l1_notes, "_notes", lambda: [])
    result = build_graph(InMemorySaver()).invoke(make_initial_state("student_sample"), CONFIG)
    briefing = result["__interrupt__"][0].value["briefing"]

    assert fake_llm.count("briefing_learner") == 1
    assert {s["origin"] for s in briefing["l1_sources"]} == {"llm"}
