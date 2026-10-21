"""
체험수업 레벨테스트 (app/standard/level_test.py, /level-test API) 확인. LLM을 쓰지 않는다.
"""

from app.standard.level_test import load_level_test, score
from app.standard.levels import sentence_level


def section_ids(level: int) -> list[str]:
    section = next(s for s in load_level_test()["levels"] if s["level"] == level)
    return [g["id"] for g in section["grammar"]] + [v["id"] for v in section["vocab"]]


HANGUL_OK = {f"hangul-{i}": True for i in range(1, 6)}


def test_every_item_points_to_standard_item_of_its_level():
    """load_level_test가 ID 존재와 등급 일치를 검사한다. 여기서 에러가 나면 데이터를 고칠 일이다."""
    test = load_level_test()
    assert [s["level"] for s in test["levels"]] == [1, 2, 3, 4, 5, 6]
    for section in test["levels"]:
        assert len(section["grammar"]) + len(section["vocab"]) >= test["min_answered"]


def test_questions_and_examples_stay_within_their_level():
    """N급 문항의 질문·예시 답에 N급보다 어려운 단어가 없어야 한다. 1급 학생이 1급 질문을 알아들어야 한다."""
    over = []
    for section in load_level_test()["levels"]:
        for g in section["grammar"]:
            for text in (g["question"], g["example"]):
                hard = [w for w in sentence_level(text)["words"] if w["level"] > section["level"]]
                if hard:
                    over.append((g["id"], text, hard))
    assert not over, over


def test_cannot_read_hangul_means_beginner():
    answers = {"hangul-1": True, "hangul-2": False, "hangul-3": False, "hangul-4": True, "hangul-5": False}
    result = score(answers)
    assert result.suggested_level == 0
    assert result.suggested_name == "입문 (한글부터)"


def test_first_failed_level_is_the_level_to_learn():
    answers = {**HANGUL_OK, **{i: True for i in section_ids(1)}}
    answers.update({i: n < 4 for n, i in enumerate(section_ids(2))})  # 2급 12개 중 4개만 맞음
    result = score(answers)
    assert result.suggested_level == 2
    assert [r.status for r in result.levels[:3]] == ["passed", "failed", "untested"]


def test_ran_out_of_time_suggests_next_level():
    """1급만 통과하고 2급은 못 봤으면 2급을 추천한다 (확인 못 했다는 이유와 함께)."""
    result = score({**HANGUL_OK, **{i: True for i in section_ids(1)}})
    assert result.suggested_level == 2
    assert "충분히 확인하지 못했다" in result.reason


def test_too_few_answers_is_not_a_verdict():
    result = score({**HANGUL_OK, **{i: False for i in section_ids(1)[:3]}})  # 1급 3문항만 봄
    assert result.levels[0].status == "not_enough"
    assert result.suggested_level == 1  # 한글은 읽으니 1급부터


def test_nothing_checked_gives_no_suggestion():
    assert score({}).suggested_level is None


def test_skipped_lower_levels_do_not_block():
    """고급 학생은 3급부터 볼 수 있다. 3급 통과, 4급 실패면 4급."""
    answers = {i: True for i in section_ids(3)}
    answers.update({i: False for i in section_ids(4)})
    assert score(answers).suggested_level == 4


def test_api_get_and_score(client):
    test = client.get("/level-test").json()
    assert test["hangul"]["words"][0]["word"] == "학교"
    body = client.post("/level-test/score", json={"answers": HANGUL_OK}).json()
    assert body["suggested_level"] == 1


def test_api_rejects_unknown_item_ids(client):
    res = client.post("/level-test/score", json={"answers": {"L9-g9": True}})
    assert res.status_code == 422
