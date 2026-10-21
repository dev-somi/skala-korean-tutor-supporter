"""
이 파일의 역할: 글자 층이 있는 PDF는 OCR 없이 쪽마다 글자를 뽑아 저장한다. (ADR-0014)

  PDF --pdftotext--> data/rag/text/<book>/p-001.txt

「세종한국문화」처럼 디지털로 만든 PDF는 글자가 정확해서 OCR보다 낫다.
기본은 읽는 순서(2단 편집이면 왼쪽 단 → 오른쪽 단)로 뽑는다. -layout은 두 단을 한 줄에 섞어서
(입문·5~6급 지침서에서 확인, 기술 ADR-0025) 표처럼 배치가 중요한 책에만 --layout으로 쓴다.
실행: uv run python -m app.rag.textlayer <pdf 경로> <book id> [--layout]
"""

import argparse
import re
import subprocess
from pathlib import Path

from app.rag.ocr import RAG_DIR, page_count


def text_dir(book: str) -> Path:
    return RAG_DIR / "text" / book


def run(pdf: Path, book: str, layout: bool = False) -> None:
    out_dir = text_dir(book)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = page_count(pdf)
    for page in range(1, total + 1):
        res = subprocess.run(
            ["pdftotext", *(["-layout"] if layout else []), "-f", str(page), "-l", str(page), str(pdf), "-"],
            capture_output=True,
            text=True,
        )  # 글꼴 경고(Unknown character collection)는 stderr로만 나오고 글자는 정상이다
        lines = [re.sub(r" {2,}", "  ", line).strip() for line in res.stdout.splitlines()]
        (out_dir / f"p-{page:03d}.txt").write_text("\n".join(line for line in lines if line), encoding="utf-8")
    print(f"{book}: {total}쪽 저장")
    from app.rag.pdfs import register  # pdfs가 이 모듈을 가져다 써서 여기서 가져온다

    register(book, pdf)  # 출처에서 원문 PDF를 열 때 쓴다 (기술 ADR-0030)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="글자 층이 있는 PDF를 쪽마다 글자로 저장한다")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("book", help="책 ID (예: culture1)")
    parser.add_argument("--layout", action="store_true", help="배치를 살려 뽑는다 (문화 교재)")
    args = parser.parse_args()
    run(args.pdf, args.book, args.layout)
