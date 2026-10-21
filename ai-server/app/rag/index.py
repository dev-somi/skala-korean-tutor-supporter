"""
이 파일의 역할: Parent-Child 청크를 임베딩해서 파일 색인으로 저장하고, 검색한다. (ADR-0014)

  data/rag/index/parents.jsonl   parent 전체 (브리핑에 넣는 단위)
  data/rag/index/children.jsonl  child 전체 (검색 단위)
  data/rag/index/vectors.bin     child 임베딩 (float32, child 순서와 같음)

검색 경로 두 개
  - get_sections(): 책·과·구역으로 parent를 바로 가져온다. 임베딩을 쓰지 않는다 (브리핑).
  - find_by_form(): 형태 키 태그(teaches)로 구역을 바로 가져온다 (문법 질문, 기술 ADR-0025).
  - search():       질문으로 child를 찾고, 그 parent를 돌려준다 (채팅·보충).

청크는 수천 개 수준이라 벡터 DB 없이 파이썬으로 전부 비교해도 충분히 빠르다.

색인 만들기: uv run python -m app.rag.index  (책을 주지 않으면 BOOKS 전부)
"""

import json
import math
import os
import sys
from array import array
from functools import lru_cache

import httpx
from langsmith import traceable

from app.rag.chunk import BOOKS, build_all, to_dicts
from app.rag.ocr import RAG_DIR

INDEX_DIR = RAG_DIR / "index"
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "bge-m3")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_BATCH = 32


def embed(texts: list[str]) -> list[list[float]]:
    """Ollama 임베딩 모델로 글 목록을 벡터로 바꾼다. 길이 1로 정규화해서 내적 = 코사인 유사도가 되게 한다."""
    vectors = []
    for i in range(0, len(texts), EMBED_BATCH):
        res = httpx.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": texts[i : i + EMBED_BATCH]}, timeout=300)
        res.raise_for_status()
        for vec in res.json()["embeddings"]:
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            vectors.append([x / norm for x in vec])
    return vectors


def write_jsonl(path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def read_jsonl(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def build_index(books: list[str]) -> None:
    """책들을 청크·태그하고, 핸드북 언어판을 합친 뒤 임베딩한다 (child는 한 번씩만)."""
    p, c = build_all(books)
    parents, children = to_dicts(p), to_dicts(c)
    for book in sorted({parent["book"] for parent in parents}):
        print(f"{book}: parent {sum(x['book'] == book for x in parents)}개", flush=True)

    vectors = embed([c["text"] for c in children])
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(INDEX_DIR / "parents.jsonl", parents)
    write_jsonl(INDEX_DIR / "children.jsonl", children)
    flat = array("f", (x for vec in vectors for x in vec))
    (INDEX_DIR / "vectors.bin").write_bytes(flat.tobytes())
    (INDEX_DIR / "meta.json").write_text(json.dumps({"model": EMBED_MODEL, "dim": len(vectors[0])}), encoding="utf-8")
    load_index.cache_clear()
    print(f"색인 저장: parent {len(parents)}개, child {len(children)}개, 차원 {len(vectors[0])}")


@lru_cache
def load_index() -> dict:
    """색인 파일을 한 번만 읽는다. 색인이 없으면 빈 색인 (RAG 없이도 서비스는 돈다)."""
    if not (INDEX_DIR / "meta.json").exists():
        return {"parents": {}, "children": [], "vectors": [], "dim": 0}
    dim = json.loads((INDEX_DIR / "meta.json").read_text())["dim"]
    flat = array("f")
    flat.frombytes((INDEX_DIR / "vectors.bin").read_bytes())
    vectors = [flat[i : i + dim] for i in range(0, len(flat), dim)]
    parents = {p["id"]: p for p in read_jsonl(INDEX_DIR / "parents.jsonl")}
    return {"parents": parents, "children": read_jsonl(INDEX_DIR / "children.jsonl"), "vectors": vectors, "dim": dim}


def with_source(parent: dict) -> dict:
    """parent에 화면·프롬프트에 붙일 출처 글을 덧붙인다. 출처는 코드가 만든다 (LLM이 지어내지 않게)."""
    pages = sorted(set(parent["pages"]))
    page_text = f"{pages[0]}쪽" if len(pages) == 1 else f"{pages[0]}~{pages[-1]}쪽"
    parts = [BOOKS[parent["book"]]["title"]]
    if parent["unit"]:
        parts.append(f"{parent['unit']}과")
    if not parent["section"].endswith("쪽"):  # 기본 규칙으로 자른 책은 구역 이름이 쪽 번호다
        parts.append(f"「{parent['section']}」")
    return {**parent, "source": " ".join([*parts, page_text])}


@traceable(run_type="retriever")
def get_sections(book: str, unit: int, sections: list[str] | None = None) -> list[dict]:
    """필터 경로: 책·과(·구역 이름 앞부분)로 parent를 책 순서대로 가져온다."""
    found = [
        p
        for p in load_index()["parents"].values()
        if p["book"] == book and p["unit"] == unit and (sections is None or any(p["section"].startswith(s) for s in sections))
    ]
    return [with_source(p) for p in found]


@traceable(run_type="retriever")
def find_by_form(keys: set[str], kind: str | None = None, others: set[str] = frozenset()) -> list[dict]:
    """
    필터 경로: 형태 키를 가르치는(teaches) 구역을 가져온다. 임베딩을 쓰지 않는다 (기술 ADR-0025).
    others(비교 대상 형태)를 언급(mentions)하거나 함께 가르치는 구역을 앞에 둔다 — "-어서와 구분" 같은 비교 설명.
    kind: guide | handbook | culture (BOOKS의 kind)
    """
    found = [
        p
        for p in load_index()["parents"].values()
        if keys & set(p.get("teaches", [])) and (kind is None or BOOKS[p["book"]].get("kind") == kind)
    ]
    found.sort(key=lambda p: -len(others & (set(p.get("mentions", [])) | set(p.get("teaches", [])))))
    return [with_source(p) for p in found]


def known_keys() -> set[str]:
    """색인에 teaches로 붙은 형태 키 전체 (질문의 형태를 맞춰 볼 사전)"""
    return {key for p in load_index()["parents"].values() for key in p.get("teaches", [])}


@traceable(run_type="retriever")
def search(query: str, k: int = 3, book: str | None = None, unit: int | None = None, kind: str | None = None) -> list[dict]:
    """의미 경로: child를 검색하고, 점수가 높은 순서로 서로 다른 parent k개를 돌려준다."""
    index = load_index()
    if not index["children"]:
        return []
    qvec = embed([query])[0]
    scored = []
    for child, vec in zip(index["children"], index["vectors"]):
        parent = index["parents"][child["parent_id"]]
        if (book and parent["book"] != book) or (unit and parent["unit"] != unit) or (kind and BOOKS[parent["book"]].get("kind") != kind):
            continue
        scored.append((sum(a * b for a, b in zip(qvec, vec)), child))
    scored.sort(key=lambda x: x[0], reverse=True)

    results, seen = [], set()
    for score, child in scored:
        if child["parent_id"] in seen:
            continue
        seen.add(child["parent_id"])
        results.append({**with_source(index["parents"][child["parent_id"]]), "score": round(score, 3), "matched": child["text"]})
        if len(results) == k:
            break
    return results


if __name__ == "__main__":
    build_index(sys.argv[1:] or [book for book, info in BOOKS.items() if info["layout"] != "merged"])
