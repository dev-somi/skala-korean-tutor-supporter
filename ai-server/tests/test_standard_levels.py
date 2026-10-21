"""
표준 교육과정 등급 목록(app/standard)이 맞게 읽히고, 예문 등급을 맞게 판정하는지 확인한다. (기술 ADR-0016)
LLM을 쓰지 않는다. Kiwi 형태소 분석기만 쓴다.
"""

import json

import pytest

from app.agent.lesson_prep.textbook import load_all_items
from app.standard import levels


def test_counts_per_level_match_source():
    """엑셀 원본의 등급별 개수와 같아야 한다 (가져오기에서 빠진 줄이 없다)."""
    grammar = [g["level"] for g in levels.grammar_items()]
    vocab = [v["level"] for v in levels.vocab_items()]
    assert [grammar.count(n) for n in range(1, 7)] == [45, 45, 67, 67, 56, 56]
    assert [vocab.count(n) for n in range(1, 7)] == [735, 1100, 1655, 2200, 2365, 2580]


def test_ids_are_unique():
    ids = [i["id"] for i in levels.grammar_items() + levels.vocab_items()]
    assert len(ids) == len(set(ids))


def test_textbook_map_points_to_real_items():
    """대응표의 교재 ID와 표준 ID가 모두 실제로 있어야 한다 (권위 게이트와 같은 원칙)."""
    textbook_ids = set(load_all_items())
    for textbook_id in textbook_ids:
        for sid in levels.standard_ids(textbook_id):
            assert levels.get_item(sid) is not None, (textbook_id, sid)
    grammar_ids = {i for i in textbook_ids if "-g" in i}
    assert grammar_ids <= {i for i in grammar_ids if levels.standard_ids(i)}, "대응이 없는 교재 문법이 있다"


def test_item_level():
    assert levels.get_item("std-g-007")["form"] == "을"
    assert levels.item_level("u03-g01") == 1  # -습니다, -습니까
    assert levels.item_level("u99-g99") is None


@pytest.mark.parametrize(
    "sentence, expected",
    [
        ("한국 드라마를 좋아합니다.", 1),
        ("조용합니다.", 1),  # 어근 + 하다
        ("먹지 않아요.", 1),  # 보조용언 '않다'(3급 동사)는 문법이라 세지 않는다
        ("가: 이름이 뭐예요? 나: 저는 리사예요.", 1),  # 화자 표시 '가:'를 명사로 세지 않는다
        ("이 정책은 경제 성장에 이바지했습니다.", 6),
    ],
)
def test_sentence_level(sentence, expected):
    assert levels.sentence_level(sentence)["level"] == expected


def test_word_level_does_not_borrow_other_pos():
    """품사가 맞는 표제어가 없으면 다른 품사의 등급을 빌려 오지 않는다 ('가'는 명사 5급만 있다)."""
    assert levels.word_level("가", "명사") == 5
    assert levels.word_level("가", "동사") is None
    assert levels.word_level("가다", "동사") == 1


def test_combined_headwords_are_split():
    """'그02/그01'처럼 품사가 여럿인 표제어가 한 칸에 묶인 206개도 글자로 찾을 수 있어야 한다."""
    assert levels.word_level("그", "관형사") == 1
    assert levels.word_level("있다", "동사") == 1
    assert all("/" not in v["word"] for v in levels.vocab_items())


def test_filter_examples_keeps_hard_ones_for_teacher():
    result = levels.filter_examples(["한국 음식을 먹습니다.", "이 정책은 경제 성장에 이바지했습니다."], max_level=1)
    assert [r["sentence"] for r in result["fit"]] == ["한국 음식을 먹습니다."]
    hard = result["too_hard"][0]
    assert {w["word"] for w in hard["hard_words"]} == {"정책", "경제", "성장", "이바지"}


def test_textbook_examples_are_level_1():
    """세종학당 한국어 1의 예문은 거의 다 1급이어야 한다. 판정기가 엉뚱하게 높이 잡지 않는지 보는 회귀 검사."""
    data_dir = levels.get_data_dir() / "textbook"
    sentences = []
    for path in sorted(data_dir.glob("unit_*.json")):
        unit = json.loads(path.read_text(encoding="utf-8"))
        sentences += [v["example"] for v in unit["vocabulary"] if v["example"]]
        sentences += [e for g in unit["grammar"] for e in g["examples"]]
    if not sentences:
        pytest.skip("교재 데이터가 없다 (저장소에 넣지 않는 데이터)")
    over = [s for s in sentences if (levels.sentence_level(s)["level"] or 0) > 1]
    assert len(over) / len(sentences) < 0.05, over


def test_api_grammar_filter_and_textbook_links(client):
    body = client.get("/standard/grammar", params={"level": 1}).json()
    assert body["total"] == 45
    assert body["source"]["license"].startswith("공공누리")
    eul = next(g for g in body["items"] if g["id"] == "std-g-007")
    assert eul["textbook"] == [{"book": "바로 배워 바로 쓰는 세종학당 한국어 1", "item_id": "u03-g02", "unit_no": 3}]
    # 관련형으로도 찾는다 ("를" → 을)
    found = client.get("/standard/grammar", params={"q": "를"}).json()["items"]
    assert "std-g-007" in [g["id"] for g in found]


def test_api_vocab_paging_and_exact_match_first(client):
    body = client.get("/standard/vocab", params={"level": 2, "limit": 10}).json()
    assert body["total"] == 1100 and len(body["items"]) == 10
    first = client.get("/standard/vocab", params={"q": "가다"}).json()["items"][0]
    assert first["word"] == "가다"
    assert client.get("/standard/vocab", params={"level": 9}).status_code == 422


def test_api_grammar_category_filter_and_counts(client):
    """분류(원본 엑셀의 '분류' 칸)로 거르고, 분류별 개수는 등급·검색어만 적용한 기준으로 준다."""
    body = client.get("/standard/grammar", params={"level": 1, "category": "조사"}).json()
    assert body["total"] == body["categories"]["조사"]
    assert all(g["category"] == "조사" for g in body["items"])
    assert sum(body["categories"].values()) == 45  # 1급 전체
    everything = client.get("/standard/grammar").json()["categories"]
    assert everything == {"조사": 60, "선어말어미": 4, "연결어미": 67, "종결어미": 62, "전성어미": 7, "표현": 136}


def test_pos_parts_match_exactly():
    """'명사'가 '의존명사'에 걸리면 안 된다. 묶인 품사는 쪼개서 각각 맞춘다."""
    assert levels.pos_parts("수사.관형사/명사") == ["수사", "관형사", "명사"]
    assert "명사" not in levels.pos_parts("의존명사")


def test_api_vocab_pos_filter_and_counts(client):
    body = client.get("/standard/vocab", params={"pos": "명사", "limit": 200}).json()
    assert all("명사" in levels.pos_parts(v["pos"]) for v in body["items"])
    assert not any(v["pos"] == "의존명사" for v in body["items"])
    counts = body["pos_counts"]
    assert counts["명사"] == 7423 and counts["의존명사"] == 121 and counts["줄어든말"] == 9
    assert body["total"] == counts["명사"]
    level1 = client.get("/standard/vocab", params={"level": 1, "pos": "동사"}).json()
    assert level1["total"] == level1["pos_counts"]["동사"] and level1["all_total"] == 735


def test_noun_and_dependent_noun_lookup_is_one_way():
    """Kiwi의 명사는 목록의 의존명사와도 맞춘다 ('받을 때' 1급, '때가 타다' 4급이 아님).
    Kiwi의 의존명사는 의존명사만 본다 ('본 적이 있다'의 적이 '적(敵)' 4급이 되지 않게)."""
    assert levels.word_level("때", "명사") == 1
    assert levels.sentence_level("스트레스를 받을 때 산책을 해요.")["level"] == 2
    assert levels.sentence_level("한국 음식을 먹어 본 적이 있어요?")["level"] == 1


def test_api_marks_homonyms_only_when_word_repeats(client):
    """동음이의어 번호는 같은 글자가 목록에 두 번 이상 나올 때만 보여 준다."""
    jang = client.get("/standard/vocab", params={"q": "장", "limit": 5}).json()["items"]
    assert jang[0]["word"] == "장" and jang[0]["has_homonyms"] is True
    price = client.get("/standard/vocab", params={"q": "가격"}).json()["items"][0]
    assert price["homonym"] == "02" and price["has_homonyms"] is False  # 번호는 있어도 목록에 한 번뿐
    grammar = client.get("/standard/grammar", params={"q": "은"}).json()["items"]
    assert [g["has_homonyms"] for g in grammar if g["form"] == "-은"] == [True, True]  # -은 2급 관형사형 / -은 2급
    assert [g["has_homonyms"] for g in grammar if g["form"] == "은"] == [False]  # 조사 은1은 목록에 한 번뿐
