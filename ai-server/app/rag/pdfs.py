"""
이 파일의 역할: 출처로 찾은 교재를 선생님 컴퓨터의 원본 PDF에서 그 쪽으로 바로 연다. (기술 ADR-0030)

  data/rag/pdfs.json = {책 ID: "/절대/경로.pdf"}   ← ocr·textlayer를 돌리면 자동 기록, 이미 색인한 책은 scan으로
  출처의 쪽(책에 인쇄된 쪽) → PDF 쪽 → Chrome에서 file:///…pdf#page=N

- 브라우저는 로컬 파일을 열 수 없어서 로컬에서 도는 ai-server가 대신 연다. 서버와 화면이 같은 컴퓨터일 때만 된다.
- `open -a`는 URL의 #page를 버린다 → Chrome에 AppleScript로 URL을 그대로 넣는다 (TS-0002).

실행:
  uv run python -m app.rag.pdfs scan <폴더>            # 폴더 아래 PDF를 쪽 수·파일명으로 책과 짝지어 등록
  uv run python -m app.rag.pdfs register <책 ID> <pdf>  # 한 권만 직접 등록
"""

import argparse
import difflib
import fcntl
import json
import os
import re
import subprocess
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.rag.chunk import BOOKS, load_pages, printed_page
from app.rag.ocr import RAG_DIR, ocr_dir, page_count
from app.rag.textlayer import text_dir

REGISTRY = RAG_DIR / "pdfs.json"
DEFAULT_VIEWER = "Google Chrome"  # #page로 쪽 이동이 되고 AppleScript로 URL을 받는다. 미리보기는 명령으로 쪽을 못 정한다
LANG_WORDS = {"en": ("영어", "english"), "ja": ("일본어", "japanese")}


def load() -> dict[str, str]:
    return json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {}


def register(book: str, pdf: Path) -> None:
    """한 줄 기록. 일괄 색인이 책 여러 권을 동시에 OCR하므로 파일을 잠그고 읽고-고치고-쓴다."""
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        registry = load() | {book: str(pdf.resolve())}
        partial = REGISTRY.with_suffix(".part")
        partial.write_text(json.dumps(registry, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        partial.replace(REGISTRY)


def resolve(book: str) -> str | None:
    """PDF를 열 책 ID. 언어판을 합친 핸드북은 등록된 판(영어판 먼저)으로 연다. 쪽 번호는 판끼리 같다."""
    registry = load()
    if BOOKS.get(book, {}).get("layout") != "merged":
        return book if book in registry else None
    series = BOOKS[book]["series"]
    editions = sorted((b for b, info in BOOKS.items() if info.get("series") == series and b != book), key=lambda b: BOOKS[b]["lang"] != "en")
    return next((b for b in editions if b in registry), None)


def available() -> list[str]:
    """원본 PDF를 열 수 있는 책 ID (합친 핸드북 포함). 화면이 "원문 열기" 버튼을 보일지 정한다."""
    registry = load()
    return sorted(book for book in BOOKS if resolve(book) and Path(registry[resolve(book)]).is_file())


@lru_cache
def page_table(book: str) -> dict[int, int]:
    """{인쇄 쪽: PDF 쪽}. 청크가 pages에 인쇄 쪽을 넣은 규칙과 같게 만든다 (app.rag.chunk)."""
    layout = BOOKS[book]["layout"]
    if layout in ("sections", "pages", "ocr_page"):
        pages = [(printed_page(page["lines"]), page["page"]) for page in load_pages(book)]
        offsets = sorted(pdf - printed for printed, pdf in pages if printed)
        usual = offsets[len(offsets) // 2] if offsets else 0
        table: dict[int, int] = {}
        # OCR이 쪽 번호를 잘못 읽으면(9 → "92") 같은 인쇄 쪽에 PDF 쪽이 둘 생긴다 → 이 책의 보통 차이에 가까운 쪽
        for printed, pdf in sorted((p for p in pages if p[0]), key=lambda p: abs(p[1] - p[0] - usual)):
            table.setdefault(printed, pdf)
        # 쪽 번호가 없는 쪽(과 표지 등)은 청크가 PDF 쪽을 대신 넣었다. 인식된 쪽 번호와 겹치면 인식된 쪽이 이긴다
        for printed, pdf in pages:
            if not printed:
                table.setdefault(pdf, pdf)
        return table
    if layout == "text_pages":  # chunk_text_pages: 인쇄 쪽 = PDF 쪽 - 1
        first, last = BOOKS[book]["pages"]
        return {page - 1: page for page in range(first, last + 1)}
    return {}  # text_page: 인쇄 쪽 = PDF 쪽


def pdf_page(book: str, printed: int) -> int:
    return page_table(book).get(printed, printed)


def file_url(pdf: str, page: int) -> str:
    return f"{Path(pdf).as_uri()}#page={page}"


def open_pdf(book: str, printed: int) -> dict:
    """원본 PDF를 그 쪽으로 연다. 실패해도 예외 대신 이유를 돌려준다 (화면이 토스트로 보여 준다)."""
    edition = resolve(book)
    if not edition:
        return {"opened": False, "message": "이 교재의 PDF가 등록되지 않았어요. README의 'PDF 등록'을 참고하세요."}
    pdf = load()[edition]
    if not Path(pdf).is_file():
        return {"opened": False, "message": f"등록된 PDF를 찾을 수 없어요: {pdf}"}
    if sys.platform != "darwin":
        return {"opened": False, "message": "PDF 바로 열기는 macOS에서만 돼요."}
    page = pdf_page(edition, printed)
    viewer = os.getenv("PDF_VIEWER", DEFAULT_VIEWER)
    script = [
        "on run argv",
        f'tell application "{viewer}"',
        "activate",
        "if (count of windows) = 0 then make new window",
        "tell front window to make new tab with properties {URL:item 1 of argv}",
        "end tell",
        "end run",
    ]
    args = [arg for line in script for arg in ("-e", line)]
    result = subprocess.run(["osascript", *args, file_url(pdf, page)], capture_output=True, text=True)
    if result.returncode == 0:
        return {"opened": True, "page": page}
    # AppleScript로 탭을 못 만드는 앱이면 기본 앱으로 파일만 연다 (쪽 이동 없음)
    subprocess.run(["open", pdf], check=False)
    return {"opened": True, "page": None, "message": f"{viewer}로 쪽을 지정하지 못해 첫 쪽부터 열었어요 ({result.stderr.strip()})"}


# ---------------------------------------------------------------------------
# scan: 이미 색인한 책의 PDF를 폴더에서 찾는다
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    return re.sub(r"[\s_()\[\]\-.]+", "", unicodedata.normalize("NFC", text).lower())  # macOS 파일명은 NFD


def last_extracted_page(book: str) -> int | None:
    """OCR·글자 추출을 한 마지막 PDF 쪽 (파일 이름 p-NNN의 NNN)."""
    files = [*ocr_dir(book).glob("p-*.json"), *text_dir(book).glob("p-*.txt")]
    return max((int(f.stem[2:]) for f in files), default=None)


def match_score(book: str, pdf: Path, pdf_pages: int, last: int) -> float:
    """0이면 후보가 아니다. 쪽 수가 같으면 크게, 파일명이 제목과 비슷할수록 더 준다."""
    if pdf_pages < last:
        return 0
    title, name = BOOKS[book]["title"], unicodedata.normalize("NFC", pdf.stem)
    # 제목의 권 번호(1, 5A…)와 판 언어(영어판·일본어판)는 파일명에도 있어야 한다
    for volume in re.findall(r"\b\d[AB]?\b", title):
        if not re.search(rf"(?<![0-9A-Za-z]){volume}(?![0-9A-Za-z])", name, re.IGNORECASE):
            return 0
    lang = BOOKS[book]["lang"]
    if BOOKS[book]["kind"] == "handbook" and lang in LANG_WORDS and not any(w in name.lower() for w in LANG_WORDS[lang]):
        return 0
    similarity = difflib.SequenceMatcher(None, normalize(title), normalize(name)).ratio()
    return (1.0 if pdf_pages == last else 0.3) + similarity


def scan(folder: Path) -> dict[str, Path]:
    pdfs = []
    for pdf in sorted(folder.rglob("*.pdf")):
        try:
            pdfs.append((pdf, page_count(pdf)))
        except (subprocess.CalledProcessError, ValueError):
            print(f"  건너뜀 (쪽 수를 못 읽음): {pdf}")
    found = {}
    for book, info in BOOKS.items():
        last = last_extracted_page(book)
        if info["layout"] == "merged" or last is None:
            continue
        scored = [(match_score(book, pdf, pages, last), pdf) for pdf, pages in pdfs]
        score, best = max(scored, default=(0, None), key=lambda s: s[0])
        if score > 0:
            found[book] = best
    return found


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="교재 원본 PDF 위치를 등록한다")
    sub = parser.add_subparsers(dest="command", required=True)
    scan_cmd = sub.add_parser("scan", help="폴더 아래 PDF를 책과 짝지어 등록")
    scan_cmd.add_argument("folder", type=Path)
    reg_cmd = sub.add_parser("register", help="한 권 등록")
    reg_cmd.add_argument("book", choices=sorted(BOOKS))
    reg_cmd.add_argument("pdf", type=Path)
    args = parser.parse_args()

    if args.command == "register":
        register(args.book, args.pdf)
        print(f"{args.book} → {args.pdf.resolve()}")
    else:
        found = scan(args.folder.expanduser())
        for book, pdf in found.items():
            register(book, pdf)
            print(f"  {book:24} → {pdf}")
        missing = [b for b, info in BOOKS.items() if info["layout"] != "merged" and b not in load()]
        print(f"{len(found)}권 등록. 못 찾은 책: {', '.join(missing) or '없음'} (register로 직접 등록)")
