"""
이 파일의 역할: catalog.json의 책을 한 권 단위로 글자로 뽑고(OCR·글자 층), 끝나면 색인을 만든다. (기술 ADR-0031)
  --workers N이면 책 N권을 동시에 뽑는다 (한 권은 항상 한 스레드가 맡는다)

  한 권 끝날 때마다 data/rag/batch/state.json 에 기록하고 data/rag/batch/batch.log 에 남긴다.
  중간에 끊겨도(Ctrl+C, 잠자기, 전원) 같은 명령을 다시 실행하면 끝난 책은 건너뛰고,
  하던 책은 끝난 쪽 다음부터 잇는다 (ocr.run이 이미 OCR한 쪽을 건너뛴다).

실행 (ai-server 폴더에서):
  caffeinate -is uv run python -m app.rag.batch run ~/Desktop/한국어            # 전부, tier 순서로
  caffeinate -is uv run python -m app.rag.batch run ~/Desktop/한국어 --index    # 다 뽑은 뒤 색인까지
  uv run python -m app.rag.batch run ~/Desktop/한국어 --only ko1_textbook       # 한 권만
  uv run python -m app.rag.batch run ~/Desktop/한국어 --max-tier 4              # 언어판(tier 5)은 빼고
  caffeinate -is uv run python -m app.rag.batch run ~/Desktop/한국어 --workers 4 # 책 4권을 동시에 (OCR은 외부 프로그램이라 스레드로 충분)
  uv run python -m app.rag.batch status                                         # 진행 상황
"""

import argparse
import fcntl
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from app.rag import ocr, textlayer
from app.rag.chunk import CATALOG
from app.rag.ocr import RAG_DIR

BATCH_DIR = RAG_DIR / "batch"
STATE = BATCH_DIR / "state.json"
LOG = BATCH_DIR / "batch.log"
LOCK = threading.Lock()  # 여러 책을 동시에 돌릴 때 상태 파일·로그를 한 번에 하나씩 쓴다


def log(message: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    with LOCK:
        print(line, flush=True)
        BATCH_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state: dict) -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    partial = STATE.with_suffix(".part")
    partial.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    partial.replace(STATE)


def extracted(book: dict) -> int:
    """지금까지 뽑은 쪽 수"""
    if book["layout"] == "ocr_page":
        return len(list(ocr.ocr_dir(book["id"]).glob("p-*.json")))
    return len(list(textlayer.text_dir(book["id"]).glob("p-*.txt")))


def extract(book: dict, pdf: Path) -> None:
    if book["layout"] == "ocr_page":
        ocr.run(pdf, book["id"], ja=book.get("ja", False))  # 이미 OCR한 쪽은 건너뛴다
    else:
        textlayer.run(pdf, book["id"])


def update(state: dict, book_id: str, **fields) -> None:
    """한 권의 상태를 바꾸고 바로 저장한다 (스레드 여러 개가 같은 state를 쓴다)"""
    with LOCK:
        state[book_id] = state.get(book_id, {}) | fields
        save_state(state)


def process(book: dict, folder: Path, state: dict, label: str) -> None:
    """한 권 뽑기. 실패해도 예외를 밖으로 내지 않는다 (다른 책은 계속 간다)"""
    pdf = folder / book["file"]
    if not pdf.is_file():
        update(state, book["id"], status="failed", error=f"파일 없음: {pdf}")
        log(f"{label} {book['id']} 실패: 파일 없음 {pdf}")
        return
    log(f"{label} {book['id']} 시작 — {book['title']} ({book['pages']}쪽, {book['layout']}, 이미 {extracted(book)}쪽)")
    update(state, book["id"], status="running", started=f"{datetime.now():%Y-%m-%d %H:%M:%S}")
    started = time.monotonic()
    try:
        extract(book, pdf)
    except Exception as exc:  # noqa: BLE001 — 한 권이 실패해도 다음 책으로 넘어간다
        update(state, book["id"], status="failed", error=f"{type(exc).__name__}: {exc}", pages_done=extracted(book))
        log(f"{book['id']} 실패: {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}")
        return
    seconds = round(time.monotonic() - started)
    done = extracted(book)
    with LOCK:
        state[book["id"]] = {k: v for k, v in state.get(book["id"], {}).items() if k != "error"}
    update(state, book["id"], status="done", pages_done=done, seconds=seconds, finished=f"{datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"{book['id']} 완료: {done}쪽, {seconds // 60}분 {seconds % 60}초")


def run(folder: Path, only: set[str] | None, max_tier: int, build: bool, workers: int = 1) -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    lock = open(BATCH_DIR / "lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # 프로세스가 끝나면 OS가 풀어 준다
    except BlockingIOError:
        raise SystemExit("이미 다른 batch가 돌고 있다 (data/rag/batch/lock). status로 진행 상황을 본다")
    books = [b for b in CATALOG["books"] if b["tier"] <= max_tier and (not only or b["id"] in only)]
    state = load_state()
    todo = [b for b in books if state.get(b["id"], {}).get("status") != "done"]
    # 전원·잠자기·강제 종료로 끊기면 상태가 running으로 남는다 → 끊긴 책으로 보고 이어서 한다
    for book in todo:
        if state.get(book["id"], {}).get("status") == "running":
            log(f"{book['id']}: 지난번에 끊김 ({extracted(book)}/{book['pages']}쪽) → 이어서 한다")
    log(f"시작: {len(books)}권 중 {len(todo)}권 남음 (끝난 {len(books) - len(todo)}권은 건너뜀), 동시에 {workers}권")

    # tier 순서대로 넣으면 앞 책부터 잡는다. 끊기면(Ctrl+C·전원) 하던 책들이 running으로 남고 다음 실행 때 잇는다
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, book in enumerate(todo, 1):
            pool.submit(process, book, folder, state, f"[{n}/{len(todo)}]")

    failed = [b["id"] for b in books if state.get(b["id"], {}).get("status") != "done"]
    log(f"글자 뽑기 끝. 못 끝낸 책 {len(failed)}권: {', '.join(failed) or '없음'}")
    if build:
        from app.rag.index import BOOKS, build_index  # 임베딩 서버(Ollama)가 필요할 때만 가져온다

        log("색인 시작 (이미 임베딩한 조각은 캐시에서 꺼낸다)")
        build_index([book for book, info in BOOKS.items() if info["layout"] != "merged" and info.get("index", True)])
        log("색인 완료")


def status() -> None:
    state = load_state()
    totals: dict[str, int] = {}
    for book in CATALOG["books"]:
        entry = state.get(book["id"], {})
        mark = entry.get("status", "pending")
        totals[mark] = totals.get(mark, 0) + 1
        note = entry.get("error", "")
        print(f"tier {book['tier']}  {mark:8} {extracted(book):4}/{book['pages']:<4} {book['id']:26} {note}")
    print(" · ".join(f"{k} {v}권" for k, v in sorted(totals.items())))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="catalog.json의 책을 한 권씩 뽑고 색인한다")
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("folder", type=Path, help="자료 폴더 (catalog.json의 file이 이 폴더 기준)")
    run_cmd.add_argument("--only", help="쉼표로 나눈 책 ID")
    run_cmd.add_argument("--max-tier", type=int, default=5)
    run_cmd.add_argument("--index", action="store_true", help="다 뽑은 뒤 색인까지 만든다")
    run_cmd.add_argument("--workers", type=int, default=1, help="동시에 뽑을 책 수 (기본 1)")
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "status":
        status()
    else:
        run(args.folder.expanduser(), set(args.only.split(",")) if args.only else None, args.max_tier, args.index, args.workers)
