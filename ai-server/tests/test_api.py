"""
이 파일의 역할: ai-server API를 가짜 LLM으로 테스트한다.

  - /intake: 권위 게이트가 없는 교재 ID·지원하지 않는 언어를 지우고 경고한다
  - /prep: SSE 이벤트 순서(started → node_finished… → review_required → … → done), 재개, 파일 내려받기
  - Spring이 보낸 profile을 파일 대신 쓴다
"""

import json

import pytest

from app.agent.lesson_prep.schemas import CATEGORIES
from tests.conftest import FAKE_INTAKE

PROFILE = {
    "student_id": "stu-7",
    "name": "Emma (가상 인물)",
    "native_language": "en",
    "level": "초급 1",
    "goals": ["여행"],
    "interests": ["K-pop"],
    "weaknesses": ["std-g-001"],
    "weakness_notes": ["받침 발음"],
    "lesson_history": [{"lesson_no": 1, "unit_no": 2, "item_ids": ["std-g-001", "std-v-00142"]}],
    "next_unit": 3,
    "notes": "",
}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def start_prep(client, thread_id="lesson-1"):
    body = {"thread_id": thread_id, "profile": PROFILE, "target_lang": "en", "output_subdir": "stu-7/lesson-1"}
    res = client.post("/prep/start", json=body)
    assert res.status_code == 200
    return parse_sse(res.text)


def test_intake_gate_removes_unknown_ids(client):
    res = client.post("/intake", json={"text": "일본인 대학생 유이 ..."})
    assert res.status_code == 200
    body = res.json()
    ids = [w["item_id"] for w in body["draft"]["weaknesses"]]
    assert ids == [None, "std-g-001", None]  # 없는 ID만 지워지고 설명은 남는다
    assert any("std-g-999" in w for w in body["warnings"])


def test_intake_gate_clears_unsupported_language(client, monkeypatch):
    monkeypatch.setitem(FAKE_INTAKE, "native_language", "zh")
    body = client.post("/intake", json={"text": "중국인 학생"}).json()
    assert body["draft"]["native_language"] is None
    assert any("zh" in w for w in body["warnings"])


def test_intake_uses_fast_tier(client, fake_llm):
    client.post("/intake", json={"text": "유이"})
    assert ("student_intake", "fast") in fake_llm.tiers


def test_intake_requires_level_and_never_guesses(client, monkeypatch):
    """현재 수준이 메모에 없으면 비워 두고 경고한다 (기획 ADR-0018)."""
    monkeypatch.setitem(FAKE_INTAKE, "standard_level", None)
    body = client.post("/intake", json={"text": "유이"}).json()
    assert body["draft"]["standard_level"] is None
    assert any("레벨테스트" in w for w in body["warnings"])


def test_intake_gate_clears_out_of_range_level_and_unknown_persona(client, monkeypatch):
    monkeypatch.setitem(FAKE_INTAKE, "standard_level", 9)
    monkeypatch.setitem(FAKE_INTAKE, "persona", "kpop")
    body = client.post("/intake", json={"text": "유이"}).json()
    assert body["draft"]["standard_level"] is None
    assert body["draft"]["persona"] is None
    assert any("kpop" in w for w in body["warnings"])


def test_prep_streams_until_review(client, fake_llm):
    events = start_prep(client)
    names = [name for name, _ in events]

    assert names[0] == "started"
    assert names[-1] == "review_required"
    finished = [data["node"] for name, data in events if name == "node_finished"]
    assert finished[:2] == ["load_profile", "load_textbook"]
    assert "briefing" in finished
    assert "write_slides" in finished

    payload = events[-1][1]
    assert payload["briefing"]["grammar_points"][0]["item_id"] == "std-g-030"
    assert set(payload["drafts"]) == set(CATEGORIES)
    # 파일이 아니라 요청으로 받은 프로필을 썼다
    personal_values = next(values for name, values in fake_llm.calls if name == "briefing_personal")
    assert "Emma" in personal_values["learner"]


def test_resume_to_done(client):
    start_prep(client)
    state = client.get("/prep/lesson-1/state").json()
    assert state["status"] == "review_required"

    decisions = {c: {"action": "approve"} for c in CATEGORIES}
    res = client.post("/prep/lesson-1/resume", json={"decisions": decisions})
    events = parse_sse(res.text)
    assert events[-1][0] == "done"
    done = events[-1][1]
    assert done["pptx_file"] is None  # PPT는 만들지 않는다 (ADR-0015)
    assert set(done["plan"]) == set(CATEGORIES)
    assert [s["stage"] for s in done["briefing"]["slide_plan"]["slides"]][0] == "warmup"
    assert client.get("/prep/lesson-1/state").json()["status"] == "done"


def test_edit_keeps_unsent_field(client):
    review = start_prep(client)[-1][1]
    decisions = {c: {"action": "approve"} for c in CATEGORIES}
    decisions["review"] = {"action": "edit", "script": "고친 대본"}  # explanation은 보내지 않음
    done = parse_sse(client.post("/prep/lesson-1/resume", json={"decisions": decisions}).text)[-1][1]
    assert done["drafts"]["review"]["script"] == "고친 대본"
    assert done["drafts"]["review"]["explanation"] == review["drafts"]["review"]["explanation"]


def test_resume_errors(client):
    assert client.post("/prep/nope/resume", json={"decisions": {"review": {"action": "approve"}}}).status_code == 404
    start_prep(client)
    bad = client.post("/prep/lesson-1/resume", json={"decisions": {"review": {"action": "feedback"}}})
    assert bad.status_code == 422  # feedback 글 없음


def test_files_blocks_other_paths(client):
    assert client.get("/files/../pyproject.toml").status_code == 404
    assert client.get("/files/checkpoints.db").status_code == 404


def test_graph_error_becomes_error_event(client, fake_llm, monkeypatch):
    def boom(*args, **kwargs):
        raise TimeoutError("slow")

    from app.agent.lesson_prep import llm

    monkeypatch.setattr(llm, "call_llm", boom)
    events = start_prep(client, "lesson-err")
    name, data = events[-1]
    assert name == "error"
    assert data["retryable"] is True
