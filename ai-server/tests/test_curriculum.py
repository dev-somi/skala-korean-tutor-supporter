"""
이 파일의 역할: 단원 시트 만들기를 테스트한다 (기술 ADR-0032).

  - 지침서 글 규칙: 문법 후보("'-어요'의 의미를 설명"), 붙임표 보정, 예문 고르기
  - 표준 목록의 뜻 번호·다른 꼴("-다가1(1)", "에서부터(서부터)")도 형태로 맞춘다
  - (지침서 색인이 있을 때만) 자동 초안 vs 손으로 만든 교재 JSON: 문법은 전부 맞고, 어휘는 틀린 것이 없다
"""

import pytest

from app.agent.grammar_qa import match_forms, standard_forms
from app.curriculum import extract
from app.rag import index as rag_index


def parent(section: str, text: str, pages=(10,), teaches=(), mentions=()) -> dict:
    return {"section": section, "text": text, "pages": list(pages), "teaches": list(teaches), "mentions": list(mentions)}


def test_grammar_candidates_from_overview_and_content_line():
    overview = parent(
        "학습 목표·수업 개요",
        "학습 내용\n어휘 및 표현\n문법\n습니다/습니까, 을, 도\n- 그림과 보기 대화를 통해 '-습니다/-습니까'의 의미를\n설명한다.",
    )
    assert extract.grammar_candidates([overview]) == ["-습니다", "-습니까", "을", "도"]


def test_section_names_are_not_taken_as_forms():
    # "어휘 및 표현"에 붙임표를 붙이면 match_forms가 뒤를 잘라 "-어"로 맞춘다 → 글자 그대로 맞을 때만
    overview = parent("학습 목표·수업 개요", "어휘 및 표현\n문법\n이, 이 아니다")
    assert extract.grammar_candidates([overview]) == ["이", "이 아니다"]


def test_standard_forms_strip_sense_numbers_and_split_alternates():
    assert standard_forms("-다가1(1)") == ["-다가"]
    assert standard_forms("에서부터(서부터)") == ["에서부터", "서부터"]
    assert standard_forms("-(으)면") == ["-(으)면"]
    assert match_forms(["-다가"])[0]["level"] == 2


def test_headword_item_prefers_own_form():
    # "에서부터"는 "부터"(1급)의 관련형이기도 하지만, 표제어가 에서부터인 2급 항목을 고른다
    assert extract.headword_item("에서부터")["form"] == "에서부터(서부터)"


def test_example_lines_keep_polite_sentences_only():
    text = "• 노래가 좋습니다.\n• 한국 노래 1~2개를 예시로 들려준다.\n교 (빵 사진을 보여 주며) 빵이에요.\n따라 하세요. 빵, 빵, 빵."
    assert extract.example_lines(text) == ["노래가 좋습니다.", "빵이에요."]


def test_vocab_words_from_gloss_and_repeat_lines():
    section = parent("어휘 및 표현_일상생활", "노래 song\n드라마 drama\n교 따라\n하세요. 음식, 음식, 음식.")
    words = [w for w, _, _ in extract.vocab_words([section])]
    assert words == ["노래", "드라마", "음식"]


def has_materials() -> bool:
    from app.agent.lesson_prep.textbook import get_data_dir

    if not (rag_index.INDEX_DIR / "parents.jsonl").exists() or not (get_data_dir() / "textbook" / "unit_02.json").exists():
        return False
    return any(p["book"] == "ko1_guide" for p in rag_index.load_index()["parents"].values())


needs_index = pytest.mark.skipif(not has_materials(), reason="지침서 색인(data/rag)과 교재 JSON(data/textbook)이 있어야 한다 (둘 다 git 밖)")


@needs_index
@pytest.mark.parametrize("unit_no", [2, 3, 4])
def test_draft_matches_hand_made_units(unit_no):
    from app.curriculum.evaluate import compare

    result = compare("ko1", unit_no)
    assert result["grammar"]["precision"] == 1 and result["grammar"]["recall"] == 1
    assert result["vocab"]["precision"] == 1  # 빠진 낱말은 있어도(본책 색인 전) 틀린 낱말은 없다


@needs_index
def test_old_ids_map_to_sheet_ids():
    """DB 이전용 대응: 옛 교재 ID → 변환한 시트의 ID와 같다 (문법은 첫 표준 ID, 표준에 없는 어휘는 표현 ID)"""
    from app.agent.lesson_prep.textbook import load_unit
    from app.curriculum.convert_textbook import convert
    from app.curriculum.ids import to_new

    sheet = convert(2).model_dump()
    assert to_new("u02-g01") == sheet["grammar"][0]["id"] == "std-g-001"
    assert to_new("u02-g02") == "std-g-037"
    assert to_new("u02-d01") == "ko1-u02-d01"
    assert to_new("std-g-001") == "std-g-001" and to_new(None) is None
    assert {to_new(v["id"]) for v in load_unit(2)["vocabulary"]} == {v["id"] for v in sheet["vocabulary"]}


def sheet_profile(**extra) -> dict:
    return {
        "student_id": "stu-1", "name": "유이", "native_language": "ja", "level": "", "goals": [],
        "weaknesses": [], "lesson_history": [], "next_unit": 5, **extra,
    }


@needs_index
def test_lesson_prep_reads_draft_sheet_and_old_ids():
    from app.agent.lesson_prep import nodes

    profile = nodes.load_profile({"profile": sheet_profile(weaknesses=["u02-g01"], lesson_history=[{"lesson_no": 1, "unit_no": 2, "item_ids": ["u02-v05"], "understanding": {"u02-v05": "shaky"}}])})["profile"]
    assert profile["weaknesses"] == ["std-g-001"] and profile["lesson_history"][0]["understanding"] == {"std-v-00142": "shaky"}

    loaded = nodes.load_textbook({"profile": profile, "unit_no": None, "book": None})
    assert loaded["book"] == "ko1" and loaded["textbook_unit"]["status"] == "draft" and loaded["textbook_unit"]["unit_no"] == 5
    assert {i["id"] for i in loaded["past_items"]} == {"std-g-001", "std-v-00142"}  # 2과 시트에서 찾아온 복습 후보


@needs_index
def test_missing_sheet_is_a_clear_error():
    from app.agent.lesson_prep import nodes

    with pytest.raises(nodes.MissingUnitSheet, match="99과"):
        nodes.load_textbook({"profile": sheet_profile(), "unit_no": 99, "book": "ko1"})
