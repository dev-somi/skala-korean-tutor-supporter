"""
이 파일의 역할: 수업 후 기록 그래프(post_lesson)를 가짜 LLM으로 테스트한다.

  - 권위 게이트: 없는 ID 삭제, 중복 제거, 이미 있는 약점 추가 삭제, 해결 대상 약점을 현재 약점에 맞춤
  - Validator 불합격이면 피드백을 다시 쓰고, 최대 2번까지만 다시 쓴다
  - Validator는 저가 모델(fast)로 부른다
  - 이해도 판정: 원문에 없는 인용·다룬 항목이 아닌 장면은 버리고, 장면 점수로 confused/shaky/ok를 정한다
"""

import json

import pytest
from fastapi.testclient import TestClient

from tests.test_api import PROFILE, parse_sse

BODY = {
    "profile": PROFILE,
    "lesson": {"lesson_no": 2, "unit_no": 3, "minutes": 50, "target_lang": "ja", "plan": None},
    "raw_note": "3과 1~2 단어 함. 밥를 이라고 함. 숙제 연습문제 2번",
    "current_weaknesses": [
        {"id": 11, "item_id": "std-g-001", "description": "이/가"},
        {"id": 12, "item_id": None, "description": "받침 발음"},
    ],
}


@pytest.fixture
def client(fake_llm, monkeypatch):
    monkeypatch.setenv("CHECKPOINT_DB", ":memory:")
    from app.main import app

    with TestClient(app) as c:
        yield c


def run(client):
    res = client.post("/post-lesson", json=BODY)
    assert res.status_code == 200
    return parse_sse(res.text)


def test_gate_fixes_extraction(client):
    events = run(client)
    assert events[-1][0] == "done"
    done = events[-1][1]
    draft = done["record_draft"]

    assert draft["covered_item_ids"] == ["std-v-00136", "std-v-00185"]  # 중복·없는 ID 제거
    changes = draft["weakness_changes"]
    assert [(c["action"], c["weakness_id"], c["item_id"]) for c in changes] == [
        ("add", None, "std-g-007"),
        ("resolve", 11, "std-g-001"),  # 교재 ID로 현재 약점을 찾아 id를 채움
    ]
    assert any("받침 발음" in w for w in done["warnings"])
    assert any("std-v-99999" in w for w in done["warnings"])
    assert any("없는 약점" in w for w in done["warnings"])
    assert draft["feedback_message"]["korean_text"]
    assert done["validation"]["is_acceptable"] is True


def test_validator_rewrite_once(client, fake_llm):
    fake_llm.validator_fail_times = 1
    done = run(client)[-1][1]
    assert fake_llm.count("write_feedback") == 2
    assert done["rewrite_count"] == 1
    second = [values for name, values in fake_llm.calls if name == "write_feedback"][1]
    assert second["validator_feedback"] == "숙제가 빠졌습니다"


def test_validator_rewrite_limit(client, fake_llm):
    fake_llm.validator_fail_times = 99
    done = run(client)[-1][1]
    assert fake_llm.count("write_feedback") == 3  # 처음 1번 + 다시 2번
    assert done["validation"]["is_acceptable"] is False
    assert ("validate_feedback", "fast") in fake_llm.tiers


def test_progress_events(client):
    nodes = [d["node"] for name, d in run(client) if name == "node_finished"]
    assert nodes == ["extract", "gate", "observe", "judge", "write_feedback", "validate"]


def test_understanding_in_draft(client):
    done = run(client)[-1][1]
    understanding = {u["item_id"]: u for u in done["record_draft"]["understanding"]}
    assert set(understanding) == {"std-v-00136", "std-v-00185"}  # u03-g02는 다룬 항목이 아니라 버림
    assert understanding["std-v-00136"]["level"] == "shaky"  # error 1개(2점), 원문에 없는 asked_again은 버림
    assert understanding["std-v-00136"]["episodes"] == [{"kind": "error", "quote": "밥를 이라고 함"}]
    assert understanding["std-v-00185"]["level"] == "ok"
    assert any("장면 2개를 버렸습니다" in w for w in done["warnings"])


def judge_with(raw_note, episodes, covered=("std-g-007",)):
    from app.agent.post_lesson.graph import judge

    state = {"raw_note": raw_note, "extraction": {"covered_item_ids": list(covered)}, "episodes": episodes, "warnings": []}
    return {u["item_id"]: u for u in judge(state)["understanding"]}


def test_judge_levels_and_quote_normalization():
    note = "T: 뭘 먹어요?\nS: 밥를 먹어요.\nT: 받침이 있으면 을이에요.\nS: 음… 잘 모르겠어요\nS: 빵을 먹어요"
    ep = lambda kind, quote: {"item_id": "std-g-007", "kind": kind, "quote": quote}  # noqa: E731
    result = judge_with(note, [
        ep("error", "S: 밥를 먹어요."),  # 화자 표시가 있어도 원문과 맞춘다
        ep("re_explained", "받침이 있으면  을이에요."),
        ep("hesitation", "음... 잘 모르겠어요"),  # 말줄임표 표기 차이
        ep("correct", "빵을 먹어요"),
    ])
    assert result["std-g-007"]["score"] == 4  # 2 + 1 + 1 + 0 (바로 맞힘은 깎지 않는다)
    assert result["std-g-007"]["level"] == "confused"


def test_correct_answers_do_not_cancel_errors():
    """세 번 틀리고 네 번 맞혀도 헷갈림이다 (샘플 녹취록의 을/를)."""
    note = "S: 드라마을\nS: 노래를\nS: 음식을\nS: 빵를\nS: 책를\nS: 물을\nS: 차를"
    eps = [{"item_id": "std-g-007", "kind": k, "quote": q} for k, q in [
        ("error", "드라마을"), ("error", "빵를"), ("error", "책를"),
        ("correct", "노래를"), ("correct", "음식을"), ("correct", "물을"), ("correct", "차를"),
    ]]
    assert judge_with(note, eps)["std-g-007"]["level"] == "confused"


def test_judge_skips_items_without_episodes_and_duplicates():
    note = "S: 빵을 먹어요"
    result = judge_with(note, [{"item_id": "std-g-007", "kind": "correct", "quote": "빵을 먹어요"}] * 2, covered=("std-g-007", "std-v-00136"))
    assert list(result) == ["std-g-007"]  # 장면이 없는 u03-v01은 "모름"이라 넣지 않는다
    assert len(result["std-g-007"]["episodes"]) == 1
