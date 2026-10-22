"""
이 파일의 역할: 3A~6B 본책에서 단원 시트를 뽑는 규칙을 테스트한다 (기술 ADR-0040).

  - 쪽 머리말로 과를 정한다 (머리말이 없는 쪽은 다음 머리말 쪽을 따르고, 목차 쪽에서 끊는다)
  - 3A~4B "Grammar" 다음 줄 / 학습목표 줄, 5A~6B "문형을 배워 봅시다." 다음 줄
  - 여러 조각 문형은 조각으로 맞추되 낮은 등급 조각은 버린다
  - 어휘: 3A~4B "낱말 + • 예문", 5A~6B "• 표제 + 예문"
"""

from app.curriculum import textbook_extract as t

FAKE_BOOK = [
    {"page": 18, "text": "1과\n약속 시간에 늦으면 안 돼요\n2과\n어제 친구를 우연히 기차역에서 만났어요"},  # 목차
    {"page": 19, "text": "학습목표\n•'-으려면'을 사용하여 문장을 구성할 수 있다.\n•'으로부터'를 사용하여 문장을 구성할 수 있다."},
    {"page": 20, "text": "Vocabulary\n동아리\n• 우리 동아리는 한국 전통 노래를 배우는 동아리예요.\n듣기\n• 신입 회원 환영회에 대한 대화를 듣고 이해할 수 있다."},
    {"page": 21, "text": "1과 • 약속 시간에 늦으면 안 돼요\n가입 (하다)\n• 이 모임에 가입을 하려면 어떻게 해야 해요?"},
    {"page": 24, "text": "Grammar\n-으려면\n정의\n명동에 가려면 몇 번 버스를 타야 해요?\n동사와 결합한다."},
    {"page": 25, "text": "1과 • 약속 시간에 늦으면 안 돼요\n연습 II"},
]


def test_page_units_follow_next_header_and_stop_at_contents(monkeypatch):
    t.page_units.cache_clear()
    monkeypatch.setattr(t, "book_pages", lambda book: FAKE_BOOK)
    assert t.page_units("fake") == {19: 1, 20: 1, 21: 1, 24: 1, 25: 1}
    t.page_units.cache_clear()


def test_grammar_from_head_line_and_learning_goals():
    items = t.grammar_items(FAKE_BOOK[1:])
    assert [(i["form"], i["page"]["page"] if i["page"] else None) for i in items] == [("-으려면", 24), ("으로부터", None)]
    assert t.grammar_examples("-으려면", FAKE_BOOK[4]) == ["명동에 가려면 몇 번 버스를 타야 해요?"]


def test_compound_patterns_match_by_fragment_but_not_low_level_pieces():
    assert t.fragments("...은 -는다는 것이다") == ["-는다는 것이다"]
    assert t.fragments("-게끔 -어야 하다") == ["-게끔", "-어야 하다"]
    form, std = t.match_standard("...은 -기 나름이다")
    assert form == "...은 -기 나름이다" and std[0]["level"] >= 5
    assert t.match_standard("과연 -을까") is None  # 1급 "-을까"만 맞는다 → 5A의 학습 목표가 아니다


def test_vocab_entries_both_layouts():
    entries = [e for e, _, _ in t.vocab_entries(FAKE_BOOK[1:4])]
    assert entries == ["동아리", "가입 (하다)"]  # "듣기"는 학습목표 칸 이름
    advanced = [{"page": 16, "text": "✓ 어휘를 배워 봅시다.\n• 안정적이다\n많은 사람이 정년이 보장되는 안정적인 직장을 구하고 싶어 한다."}]
    assert [e for e, _, _ in t.vocab_entries(advanced)] == ["안정적이다"]


def test_lookup_words_splits_alternatives_and_drops_predicate():
    assert [w for w, _ in t.lookup_words("정규직/비정규직")][0] == "정규직"
    assert [w for w, _ in t.lookup_words("연봉이 높다")] == ["연봉"]
    assert [w for w, s in t.lookup_words("안정적이다") if s] == ["안정적"]
