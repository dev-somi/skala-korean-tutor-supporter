"""
이 파일의 역할: LangSmith 실행 기록을 화면용 트리로 바꾸는 부분을 테스트한다 (기술 ADR-0028).
실제 LangSmith는 부르지 않고, Client.list_runs가 돌려주는 run 모양만 흉내 낸다.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api import traces

T0 = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
TRACE_ID = uuid4()


def fake_run(name, run_type, start_s, end_s, parent=None, error=None, tokens=0, metadata=None):
    return SimpleNamespace(
        id=uuid4(),
        trace_id=TRACE_ID,
        parent_run_id=parent.id if parent else None,
        name=name,
        run_type=run_type,
        start_time=T0 + timedelta(seconds=start_s),
        end_time=T0 + timedelta(seconds=end_s) if end_s is not None else None,
        error=error,
        total_tokens=tokens,
        prompt_tokens=0,
        completion_tokens=0,
        total_cost=None,
        extra={"metadata": metadata or {}},
        inputs={"x": 1},
        outputs={"y": "가" * 3000},
        app_path=None,
    )


def test_build_tree_links_children_in_start_order():
    root = fake_run("lesson_prep", "chain", 0, 10, metadata={"thread_id": "lesson-1"})
    node = fake_run("write_explanations", "chain", 1, 6, parent=root)
    # 병렬 LLM 호출 두 개: 늦게 시작한 것을 먼저 넣어도 시작 순서로 정렬된다
    llm_b = fake_run("write_script", "llm", 2, 5, parent=node, tokens=30)
    llm_a = fake_run("write_explanation", "llm", 1.5, 4, parent=node, tokens=20, metadata={"ls_model_name": "qwen3:8b"})
    failed = fake_run("auto_review", "chain", 7, None, parent=root, error="boom")

    tree = traces.build_tree([llm_b, root, failed, node, llm_a])

    assert tree["label"] == "수업 준비"
    assert tree["thread_id"] == "lesson-1"
    assert tree["total_latency_ms"] == 10_000
    top = tree["root"]
    assert [c["name"] for c in top["children"]] == ["write_explanations", "auto_review"]
    assert top["children"][0]["label"] == "개인화 설명 쓰기"
    leaves = top["children"][0]["children"]
    assert [c["name"] for c in leaves] == ["write_explanation", "write_script"]
    assert leaves[0]["start_offset_ms"] == 1500
    assert leaves[0]["model"] == "qwen3:8b"
    assert top["children"][1]["status"] == "error"
    assert top["children"][1]["latency_ms"] is None
    # 긴 출력은 잘린다
    assert leaves[0]["outputs"].endswith("…(생략)")


def test_summary_counts_errors_and_skips_missing_cost():
    rows = [
        {"latency_ms": 1000, "total_cost": None, "status": "success", "total_tokens": 10},
        {"latency_ms": 3000, "total_cost": 0.01, "status": "error", "total_tokens": 5},
        {"latency_ms": None, "total_cost": None, "status": "running", "total_tokens": 0},
    ]
    assert traces.summary_of(rows) == {"count": 3, "errors": 1, "avg_latency_ms": 2000, "total_tokens": 15, "total_cost": 0.01}


def test_disabled_without_key(client, monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert client.get("/traces").json()["enabled"] is False
