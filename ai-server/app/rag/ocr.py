"""
이 파일의 역할: 글자 층이 없는 교재 PDF(이미지)를 쪽마다 OCR해서 JSON으로 저장한다. (ADR-0014)

  PDF --pdftoppm--> 쪽 이미지 --macOS Vision(scripts/ocr_vision.swift)--> data/rag/ocr/<book>/p-001.json

- 이미 OCR한 쪽은 건너뛴다. 중간에 멈춰도 다시 실행하면 이어서 한다.
- macOS 전용이다. 결과 JSON만 있으면 다른 OS에서도 chunk·index 단계는 돌릴 수 있다.
- 일본어판 핸드북처럼 한국어와 일본어가 섞인 쪽은 --ja로 두 번 읽어 합친다 (merge_ja).
  Vision은 앞 언어를 우선해서, 한 번에 읽으면 한쪽 언어가 깨진다.

실행: uv run python -m app.rag.ocr <pdf 경로> <book id> [--first N --last M] [--ja]
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from app.agent.lesson_prep.textbook import PROJECT_DIR

RAG_DIR = PROJECT_DIR / "data" / "rag"
SWIFT_SRC = PROJECT_DIR / "scripts" / "ocr_vision.swift"
OCR_BIN = RAG_DIR / "bin" / "ocr_vision"
DPI = 130  # 이 정도면 본문·표 글자를 충분히 읽는다. 높이면 느려지기만 한다


def ocr_dir(book: str) -> Path:
    return RAG_DIR / "ocr" / book


def ensure_binary() -> Path:
    """Swift 소스를 처음 한 번만 컴파일한다."""
    if not OCR_BIN.exists() or OCR_BIN.stat().st_mtime < SWIFT_SRC.stat().st_mtime:
        OCR_BIN.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(SWIFT_SRC), "-o", str(OCR_BIN)], check=True)
    return OCR_BIN


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise ValueError(f"쪽 수를 알 수 없음: {pdf}")


KANA = re.compile(r"[\u3040-\u30ff]")
HIRAGANA = re.compile(r"[\u3040-\u309f]")
# 히라가나가 이만큼 있어야 일본어 줄로 본다. 한국어 줄을 일본어로 잘못 읽으면 가타카나가 섞인다 ("가" → "フト")
MIN_HIRAGANA = 2


def read_lines(image: Path, binary: Path, langs: str) -> list[dict]:
    env = {**os.environ, "OCR_LANGS": langs}
    out = subprocess.run([str(binary), str(image)], capture_output=True, text=True, check=True, env=env).stdout
    return json.loads(out)["lines"]


def merge_ja(ko_lines: list[dict], ja_lines: list[dict]) -> list[dict]:
    """한국어 우선 결과에서, 일본어 우선 결과의 일본어 줄과 겹치는 줄을 일본어 줄로 바꾼다."""
    ja_only = [line for line in ja_lines if len(HIRAGANA.findall(line["text"])) >= MIN_HIRAGANA]

    def overlaps(a: dict, b: dict) -> bool:
        center = a["y"] + a["h"] / 2
        return b["y"] <= center <= b["y"] + b["h"] and a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]

    kept = [line for line in ko_lines if not any(overlaps(line, ja) for ja in ja_only)]
    return kept + ja_only


def ocr_page(pdf: Path, page: int, binary: Path, ja: bool = False) -> dict:
    """한 쪽을 이미지로 바꿔 OCR한다."""
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "p"
        subprocess.run(
            ["pdftoppm", "-r", str(DPI), "-png", "-f", str(page), "-l", str(page), "-singlefile", str(pdf), str(prefix)],
            check=True,
        )
        image = Path(f"{prefix}.png")
        lines = read_lines(image, binary, "ko-KR,en-US")
        if ja:
            lines = merge_ja(lines, read_lines(image, binary, "ja-JP,ko-KR"))
    return {"page": page, "lines": lines}


def run(pdf: Path, book: str, first: int = 1, last: int | None = None, ja: bool = False) -> None:
    binary = ensure_binary()
    out_dir = ocr_dir(book)
    out_dir.mkdir(parents=True, exist_ok=True)
    last = last or page_count(pdf)
    for page in range(first, last + 1):
        target = out_dir / f"p-{page:03d}.json"
        if target.exists():
            continue
        target.write_text(json.dumps(ocr_page(pdf, page, binary, ja), ensure_ascii=False), encoding="utf-8")
        print(f"{book} {page}/{last}", flush=True)
    from app.rag.pdfs import register  # pdfs가 이 모듈을 가져다 써서 여기서 가져온다

    register(book, pdf)  # 출처에서 원문 PDF를 열 때 쓴다 (기술 ADR-0030)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="교재 PDF를 쪽마다 OCR한다")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("book", help="책 ID (예: ko1_guide)")
    parser.add_argument("--first", type=int, default=1)
    parser.add_argument("--last", type=int)
    parser.add_argument("--ja", action="store_true", help="한국어·일본어가 섞인 책: 두 번 읽어 합친다")
    args = parser.parse_args()
    run(args.pdf, args.book, args.first, args.last, args.ja)
