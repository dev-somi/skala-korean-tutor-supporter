"""평가 채점 규칙 테스트 (LLM 호출 없음)"""

from eval.scoring import score_case, summarize

EXPECTED = {
    "covered_item_ids": ["std-v-00136", "std-g-007"],
    "optional_covered_item_ids": ["std-g-006"],
    "weakness_changes": [
        {"action": "resolve", "weakness_id": 11},
        {"action": "add", "item_id": "std-g-007", "keywords": ["을/를"]},
    ],
    "homework_item_ids": ["ko1-u03-e02"],
}


def predicted(**over):
    base = {
        "covered_item_ids": ["std-v-00136", "std-g-007"],
        "weakness_changes": [
            {"action": "add", "item_id": None, "description": "을/를 받침 구분"},  # ID 없어도 키워드로 일치
            {"action": "resolve", "weakness_id": 11, "description": "이/가"},
        ],
        "homework": [{"item_id": "ko1-u03-e02", "description": "연습 2"}],
    }
    return {**base, **over}


def test_exact_match_passes():
    s = score_case("c", EXPECTED, predicted())
    assert s.passed


def test_optional_item_is_not_penalized():
    s = score_case("c", EXPECTED, predicted(covered_item_ids=["std-v-00136", "std-g-007", "std-g-006"]))
    assert s.covered_exact and s.passed


def test_extra_item_and_missing_item():
    s = score_case("c", EXPECTED, predicted(covered_item_ids=["std-v-00136", "std-v-00709"]))
    assert (s.covered_tp, s.covered_fp, s.covered_fn) == (1, 1, 1)
    assert not s.passed


def test_extra_weakness_change_fails():
    changes = predicted()["weakness_changes"] + [{"action": "add", "item_id": "std-g-030", "description": "습니다"}]
    s = score_case("c", EXPECTED, predicted(weakness_changes=changes))
    assert not s.changes_exact and len(s.changes_extra) == 1


def test_wrong_resolve_target_fails():
    changes = [predicted()["weakness_changes"][0], {"action": "resolve", "weakness_id": 12, "description": "x"}]
    assert not score_case("c", EXPECTED, predicted(weakness_changes=changes)).changes_exact


def test_summary():
    good = score_case("a", EXPECTED, predicted())
    bad = score_case("b", EXPECTED, predicted(homework=[]))
    summary = summarize([good, bad])
    assert summary["homework_accuracy"] == 0.5
    assert summary["covered_f1"] == 1.0
    assert summary["case_pass_rate"] == 0.5
