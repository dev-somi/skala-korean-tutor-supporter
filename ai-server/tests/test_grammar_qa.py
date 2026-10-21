"""
이 파일의 역할: 문법 질문 답변(grammar_qa)과 형태 키 태그의 코드 부분을 테스트한다. (PRD F6-4, 기술 ADR-0025)
  형태 키 정규화, 책 형식별 teaches 규칙, 언어판 합치기, 근거 없는 예문 거르기, 등급 확인.
LLM과 RAG 색인은 가짜로 바꾼다 (색인 파일은 저장소에 없다).

실행 방법: uv run pytest
"""

from app.agent import grammar_qa
from app.rag.chunk import BOOKS, Parent, teaches_of
from app.rag.forms import form_keys, quoted_forms
from app.rag.handbook import clean_native, merge_editions, split_item


def test_form_keys_merge_allomorphs_and_keep_endings_apart_from_particles():
    assert form_keys("-아서/-어서/-여서(1)") == form_keys("-어서") == {"-어서"}
    assert form_keys("-(으)니까") == form_keys("-으니까/-니까") == {"-니까"}
    assert form_keys("-을 거예요/-ㄹ 거예요(1)") == {"-ㄹ_거예요"}
    assert form_keys("한테, 한테(서)") == {"한테", "한테서"}
    assert form_keys("이/가") == {"이"} and form_keys("은/는") == {"은"}
    assert form_keys("-는") == {"-는"} != form_keys("는")  # 어미 -는 ≠ 조사 는
    assert form_keys("...은 -기 나름이다") == {"-기_나름이다"}
    assert form_keys("-는 데") == {"-는_데"} != form_keys("-는데")  # 의존명사 "데"와 어미 "-는데"는 다르다
    assert form_keys("-는/-은/-ㄴ 게 어때(요)?") >= {"-는_게_어때요", "-ㄴ_게_어때요"} and "-는" not in form_keys("-는/-은/-ㄴ 게 어때(요)?")
    assert form_keys("-아/어서") == form_keys("-어/아서") == form_keys("-아/어/여서") == {"-어서"}  # 줄임 표기
    assert form_keys("-았/었어요") == {"-었어요"}


def test_quoted_forms_find_mentions_in_text():
    text = "'이다, 아니다'는 '-어서'를 쓴다. ‘...은 -기 나름이다’를 도입한다. '은/는'"
    assert {"-어서", "-기_나름이다", "은"} <= quoted_forms(text)


def test_teaches_rules_per_book_format():
    guide = Parent(id="g", book="ko1_guide", unit=11, section="문법 1", text="문법 1\n학습\n① 그림을 보면서 목표 문법 '-어서'가 '이유나 원인'의 의미임을 설명한다.")
    assert teaches_of(guide, "first_quote") == {"-어서"}
    not_grammar = Parent(id="g2", book="ko1_guide", unit=3, section="문법 2", text="목표 문법 -지 않다'가 동사 뒤에 붙어 상황을 부정함을 설명한다. '시간'")
    assert teaches_of(not_grammar, "first_quote") == {"-지_않다"}  # 여는 따옴표를 OCR이 놓친 경우, 예시 단어 '시간'은 문법이 아니다
    manual = Parent(id="m", book="ko3a_manual", unit=6, section="21쪽", text="문법 연습\n1. -나 보다, -는가 보다\n2) 영어뿐이라서")
    assert teaches_of(manual, "numbered") == {"-나_보다", "-는가_보다"}
    upper = Parent(id="u", book="ko5a_guide", unit=2, section="31쪽", text="① 읽기에 나온 문장을 통해 ‘...은 -기 나름이다’를 도입한다.")
    assert teaches_of(upper, "introduce") == {"-기_나름이다"}


def test_editions_are_merged_into_one_parent_with_translations():
    """같은 시리즈·같은 항목의 영어판·일본어판 → 한국어 글 한 벌 + translations {en, ja}"""
    korean = "문법\n-으니까/-니까\n6-2\n• 오늘은 늦었으니까 내일 이야기해요.\n'-으니까/-니까'는 행동의 이유를 나타낸다."
    en = Parent(id="a", book="practical2_handbook_en", unit=6, section="문법 6-2 -으니까/-니까", pages=[46], text=korean + "\n'-으니까' is attached to verbs to give a reason.", teaches=["-니까"])
    ja = Parent(id="b", book="practical2_handbook_ja", unit=6, section="문법 6-2 -으니까/-니까", pages=[46], text=korean + "\n「-OLI」は、動詞について行動の理由を表す。", teaches=["-니까"])
    vocab = Parent(id="c", book="practical2_handbook_ja", unit=6, section="어휘 6-1", pages=[20], text="날씨")
    merged = merge_editions([en, ja, vocab], BOOKS)
    assert [p.id for p in merged] == ["c", "practical2_handbook/6-2"]
    item = merged[1]
    assert item.book == "practical2_handbook" and item.teaches == ["-니까"]
    assert "is attached" not in item.text and "動詞" not in item.text
    assert item.translations["en"].startswith("'-으니까' is attached")
    assert item.translations["ja"].startswith("「-으니까/-니까」は")  # 깨진 표제어는 항목 이름으로


def test_split_item_separates_examples_and_explanations():
    text = "\n".join(["14 배가 너무 불러서", "-아서/-어서/-여서(1)", "• 가: 왜 한국어를 배워요?", "나: 한국 노래를 좋아해서 한국어를 배워요.",
                      "14-1 '-아서/-어서/-여서'는 동사 어간에 붙어 이유를 나타낸다.", "「-OHA」は、動詞の語について理由を表す。", "68"])
    part = split_item(text, "문법 14-1 -아서/-어서/-여서(1)")
    assert part["examples"] == ["• 가: 왜 한국어를 배워요?", "나: 한국 노래를 좋아해서 한국어를 배워요."]
    assert part["explain_ko"].startswith("'-아서")
    assert part["native"] == "「-아서/-어서/-여서」は、動詞の語について理由を表す。"


def test_clean_native_replaces_garbled_korean():
    cleaned = clean_native("「-OHA/-2A/-0」は、理由を表す。母音「H」の後には「-OM」がつく。", "-아서/-어서/-여서")
    assert cleaned.startswith("「-아서/-어서/-여서」は") and "「…」がつく" in cleaned and "OM" not in cleaned


def fake_index(monkeypatch, parents):
    """find_by_form·search·known_keys를 가짜 parent 목록으로 바꾼다."""
    def find_by_form(keys, kind=None, others=frozenset()):
        found = [p for p in parents if keys & set(p["teaches"]) and (kind is None or p["kind"] == kind)]
        return sorted(found, key=lambda p: -len(others & set(p.get("mentions", []))))

    monkeypatch.setattr(grammar_qa.rag_index, "find_by_form", find_by_form)
    monkeypatch.setattr(grammar_qa.rag_index, "search", lambda *a, **k: [])
    monkeypatch.setattr(grammar_qa.rag_index, "known_keys", lambda: {k for p in parents for k in p["teaches"]})


def test_forms_written_in_question_are_matched_without_llm(monkeypatch):
    fake_index(monkeypatch, [])
    found = grammar_qa.match_forms(grammar_qa.forms_in_text("-아서랑 -(으)니까 뭐가 달라?"))
    assert [(f["form"], f["keys"], f["level"]) for f in found] == [("-아서", ["-어서"], 1), ("-(으)니까", ["-니까"], 1)]
    assert grammar_qa.match_forms(["-뷁"]) == []
    found = grammar_qa.match_forms(grammar_qa.forms_in_text("-어/아서 어떻게 가르쳐?"))
    assert [(f["form"], f["keys"]) for f in found] == [("-어/아서", ["-어서"])]


def test_llm_forms_not_seen_in_question_are_dropped(monkeypatch):
    """'이거 어떻게 가르쳐?'에서 저가 모델이 '가르쳐'의 어미를 뽑아도 코드가 버린다."""
    fake_index(monkeypatch, [])
    monkeypatch.setattr(grammar_qa.llm, "call_llm", lambda *a, **k: {"forms": ["-어/아서"]})
    assert grammar_qa.extract_forms("이거 어떻게 가르쳐?") == []
    assert grammar_qa.in_question("-아서", "가서랑 가니까 차이") and grammar_qa.in_question("이/가", "제가 뭐예요")


def test_conjugated_question_falls_back_to_llm_and_is_validated(monkeypatch):
    """'사는/살던'은 코드로 못 뽑아서 저가 모델에 묻고, 모르는 형태는 코드가 버린다 (권위 게이트)."""
    fake_index(monkeypatch, [])
    calls = []

    def fake_llm(name, schema, values, tier="quality"):
        calls.append((name, tier))
        return {"forms": ["-는", "-던", "-없는어미"]}

    monkeypatch.setattr(grammar_qa.llm, "call_llm", fake_llm)
    found = grammar_qa.extract_forms("사는이랑 살던 차이")
    assert [(f["form"], f["level"]) for f in found] == [("-는", 2), ("-던", 3)]
    assert calls == [("grammar_forms", "fast")]


def test_points_with_invented_examples_are_removed():
    """근거에 없는 예문이 든 요점은 통째로 뺀다. '사는' 같은 한 단어 인용은 예문으로 보지 않는다."""
    points = ["'사는'은 현재를 나타낸다.", "예: '날씨가 좋아서 산책하러 가요.'", "예: '날씨가 좋아니까 산책할 거예요'"]
    kept, removed = grammar_qa.check_examples(points, "나: 날씨가 좋아서 산책하러 가요.")
    assert kept == points[:2] and removed == points[2:]


def test_answer_uses_comparison_section_first_and_marks_levels(monkeypatch):
    """비교 대상을 언급한 구역이 먼저 오고, 근거 없는 형태와 학생 등급을 넘는 형태를 코드가 표시한다."""
    handbook = {"kind": "handbook", "book": "practical1_handbook", "pages": [53], "teaches": ["-는"], "section": "문법 10-2 -는", "source": "핸드북 10과 53쪽",
                "text": "10 제목\n-는\n• 가: 지금 사는 곳이 어디예요?\n'-는'은 동사에 붙어 현재를 나타낸다.", "translations": {"ja": "「-는」は現在を表す。"}}
    plain = {"kind": "guide", "book": "ko1_guide", "pages": [40], "teaches": ["-는"], "mentions": [], "source": "지침서 A", "text": "'-는'을 설명한다."}
    compare = {"kind": "guide", "book": "ko2_guide", "pages": [41], "teaches": ["-는"], "mentions": ["-던"], "source": "지침서 B", "text": "'-는'과 '-던'을 비교한다."}
    fake_index(monkeypatch, [handbook, plain, compare])
    monkeypatch.setattr(grammar_qa.llm, "call_llm", lambda name, schema, values, tier="quality": (
        {"forms": ["-는", "-던"]} if name == "grammar_forms" else {"points": ["-는은 현재를 나타낸다."], "ai_note": "-던은 과거 회상"}
    ))

    result = grammar_qa.answer_question("사는이랑 살던 차이", "ja", 1)
    neun, deon = result["forms"]
    assert [s["source"] for s in neun["sources"]] == ["핸드북 10과 53쪽", "지침서 B", "지침서 A"]
    assert neun["sources"][0]["explain_native"] == "「-는」は現在を表す。"
    assert result["ungrounded_forms"] == ["-던"] and result["grounded"] is False
    assert result["out_of_level"] == [{"form": "-는", "level": 2}, {"form": "-던", "level": 3}]


def test_no_forms_returns_guidance_without_answer_llm(monkeypatch):
    fake_index(monkeypatch, [])
    calls = []
    monkeypatch.setattr(grammar_qa.llm, "call_llm", lambda name, *a, **k: calls.append(name) or {"forms": []})
    result = grammar_qa.answer_question("안녕하세요", "ja", None)
    assert result["forms"] == [] and "찾지 못했어요" in result["points"][0]
    assert calls == ["grammar_forms"]
