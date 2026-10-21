"""
이 파일의 역할: 일괄 색인이 끊겨도 이어서 하는지 테스트한다 (기술 ADR-0031).

  - 임베딩 캐시: 같은 글은 다시 임베딩하지 않고, 끊겨서 키 없이 남은 벡터는 버린다
  - batch: 한 권이 실패해도 다음 책으로 넘어가고, 다시 실행하면 끝난 책은 건너뛴다
"""

import time

import pytest

from app.rag import batch, index


@pytest.fixture
def rag_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(index, "RAG_DIR", tmp_path)
    monkeypatch.setattr(batch, "BATCH_DIR", tmp_path / "batch")
    monkeypatch.setattr(batch, "STATE", tmp_path / "batch" / "state.json")
    monkeypatch.setattr(batch, "LOG", tmp_path / "batch" / "batch.log")
    return tmp_path


def fake_embedder(monkeypatch):
    calls = []

    def embed_batch(texts):
        calls.append(list(texts))
        return [[float(len(t)), 1.0] for t in texts]

    monkeypatch.setattr(index, "embed_batch", embed_batch)
    return calls


def test_embed_reuses_cache_across_runs(rag_dir, monkeypatch):
    calls = fake_embedder(monkeypatch)
    assert index.embed(["가", "나나"]) == [[1.0, 1.0], [2.0, 1.0]]
    assert index.embed(["나나", "다다다", "가"]) == [[2.0, 1.0], [3.0, 1.0], [1.0, 1.0]]
    assert calls == [["가", "나나"], ["다다다"]]  # 두 번째 실행은 새 글만


def test_embed_drops_vectors_written_without_keys(rag_dir, monkeypatch):
    calls = fake_embedder(monkeypatch)
    index.embed(["가"])
    # 벡터만 쓰고 키를 쓰기 전에 끊긴 상황
    with open(index.cache_dir() / "vectors.bin", "ab") as f:
        f.write(b"\0" * 8)
    assert index.embed(["가", "라라"]) == [[1.0, 1.0], [2.0, 1.0]]
    assert calls[-1] == ["라라"]


def test_batch_continues_after_failure_and_resumes(rag_dir, monkeypatch, tmp_path):
    books = [
        {"id": "a", "file": "a.pdf", "title": "A", "pages": 1, "layout": "text_page", "tier": 1},
        {"id": "b", "file": "b.pdf", "title": "B", "pages": 1, "layout": "text_page", "tier": 1},
    ]
    monkeypatch.setitem(batch.CATALOG, "books", books)
    for b in books:
        (tmp_path / b["file"]).write_bytes(b"%PDF")
    done, fail = [], {"a"}

    def extract(book, pdf):
        if book["id"] in fail:
            raise RuntimeError("Vision 실패")
        done.append(book["id"])

    monkeypatch.setattr(batch, "extract", extract)
    monkeypatch.setattr(batch, "extracted", lambda book: 1)
    batch.run(tmp_path, None, 5, build=False)
    state = batch.load_state()
    assert state["a"]["status"] == "failed" and state["b"]["status"] == "done"

    fail.clear()
    batch.run(tmp_path, None, 5, build=False)
    assert done == ["b", "a"]  # b는 다시 하지 않는다
    assert all(v["status"] == "done" for v in batch.load_state().values())
    assert "a 실패" in (rag_dir / "batch" / "batch.log").read_text(encoding="utf-8")


def test_batch_runs_books_in_parallel(rag_dir, monkeypatch, tmp_path):
    books = [{"id": f"b{i}", "file": f"b{i}.pdf", "title": "B", "pages": 1, "layout": "text_page", "tier": 1} for i in range(4)]
    monkeypatch.setitem(batch.CATALOG, "books", books)
    for b in books:
        (tmp_path / b["file"]).write_bytes(b"%PDF")
    monkeypatch.setattr(batch, "extract", lambda book, pdf: time.sleep(0.05))
    monkeypatch.setattr(batch, "extracted", lambda book: 1)
    started = time.monotonic()
    batch.run(tmp_path, None, 5, build=False, workers=4)
    assert time.monotonic() - started < 0.15  # 4권 × 0.05초를 동시에
    assert all(batch.load_state()[b["id"]]["status"] == "done" for b in books)
