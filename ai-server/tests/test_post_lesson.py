"""
이 파일의 역할: 수업 후 기록 그래프(post_lesson)를 가짜 LLM으로 테스트한다.

  - 권위 게이트: 없는 ID 삭제, 중복 제거, 이미 있는 약점 추가 삭제, 해결 대상 약점을 현재 약점에 맞춤
  - Validator 불합격이면 피드백을 다시 쓰고, 최대 2번까지만 다시 쓴다
  - Validator는 저가 모델(fast)로 부른다
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
        {"id": 11, "item_id": "u02-g01", "description": "이/가"},
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

    assert draft["covered_item_ids"] == ["u03-v01", "u03-v02"]  # 중복·없는 ID 제거
    changes = draft["weakness_changes"]
    assert [(c["action"], c["weakness_id"], c["item_id"]) for c in changes] == [
        ("add", None, "u03-g02"),
        ("resolve", 11, "u02-g01"),  # 교재 ID로 현재 약점을 찾아 id를 채움
    ]
    assert any("받침 발음" in w for w in done["warnings"])
    assert any("u99-v99" in w for w in done["warnings"])
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
    assert nodes == ["extract", "gate", "write_feedback", "validate"]
