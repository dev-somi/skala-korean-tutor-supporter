"""
이 파일의 역할: 색인된 자료에서 단원 시트 초안(status: draft)을 만든다. (기술 ADR-0032)

  uv run python -m app.curriculum.build ko1              # 지침서에 있는 과 전부
  uv run python -m app.curriculum.build ko1 --units 5-9

- 문법·어휘는 지침서에서 코드 규칙으로 뽑는다 (app.curriculum.extract). LLM은 쓰지 않는다.
- 선생님이 검수한 시트(status: reviewed)는 덮어쓰지 않는다.
- 대화·읽기·연습은 본책·익힘책 색인이 생기면 채운다 (지금은 빈 목록 + notes에 적는다).
"""

import argparse

from app.curriculum import extract
from app.curriculum.schemas import SheetGrammar, SheetVocab, Source, UnitSheet
from app.curriculum.sheets import BOOK_SOURCES, load_sheet, save_sheet

MIN_GRAMMAR = 1  # 이보다 적게 뽑히면 notes에 적는다
MIN_VOCAB = 5


def build_unit(book: str, unit_no: int) -> UnitSheet | None:
    guide = BOOK_SOURCES[book]["guide"]
    parents = extract.unit_parents(guide, unit_no)
    if not parents:
        return None
    pages = sorted({page for p in parents for page in p["pages"]})
    notes = []

    grammar = []
    for item in extract.grammar_items(parents):
        section_pages = item["section"]["pages"] if item["section"] else pages[:1]
        grammar.append(
            SheetGrammar(
                id=item["standard_ids"][0],
                standard_ids=item["standard_ids"],
                form=item["form"],
                description=extract.grammar_description(item),
                examples=extract.grammar_examples(item),
                page=section_pages[0],
                level=item["level"],
                source=Source(book=guide, pages=section_pages),
            )
        )

    words = extract.vocab_words(parents)
    listed = {word for word, _, _ in words if extract.standard_vocab(word)}
    vocabulary, seen, n_expr = [], set(), 0
    for word, gloss, parent in words:
        std = extract.standard_vocab(word)
        if not std and extract.is_inflection(word, listed):
            continue  # "맑습니다"는 "맑다"의 활용형
        if std:
            if std["id"] in seen:
                continue
            seen.add(std["id"])
            item_id = std["id"]
        else:
            n_expr += 1
            item_id = f"{book}-u{unit_no:02d}-x{n_expr:02d}"  # 표준 목록에 없는 표현: 진도에 세지 않는다
        vocabulary.append(
            SheetVocab(
                id=item_id,
                word=word,
                meaning=gloss,
                pos=std["pos"] if std else "",
                example=extract.vocab_example(word, parent),
                page=parent["pages"][0],
                level=std["level"] if std else None,
                source=Source(book=guide, pages=parent["pages"]),
            )
        )

    if len(grammar) < MIN_GRAMMAR:
        notes.append("지침서에서 문법을 찾지 못함")
    if len(vocabulary) < MIN_VOCAB:
        notes.append(f"지침서에서 어휘를 {len(vocabulary)}개만 찾음")
    notes.append("대화·읽기·연습: 본책·익힘책 색인 전이라 비어 있음")
    return UnitSheet(
        book=book,
        unit_no=unit_no,
        title=extract.unit_titles(guide).get(unit_no, f"{unit_no}과"),
        status="draft",
        page_start=pages[0],
        page_end=pages[-1],
        vocabulary=vocabulary,
        grammar=grammar,
        notes=notes,
    )


def parse_units(text: str | None, book: str) -> list[int]:
    if not text:
        return sorted(extract.unit_titles(BOOK_SOURCES[book]["guide"]))
    first, _, last = text.partition("-")
    return list(range(int(first), int(last or first) + 1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="색인된 자료에서 단원 시트 초안을 만든다")
    parser.add_argument("book", choices=sorted(BOOK_SOURCES))
    parser.add_argument("--units", help="예: 5-9 (없으면 지침서에 있는 과 전부)")
    args = parser.parse_args()
    for unit_no in parse_units(args.units, args.book):
        existing = load_sheet(args.book, unit_no)
        if existing and existing["status"] == "reviewed":
            print(f"{unit_no:2}과 검수된 시트가 있어 건너뜀")
            continue
        sheet = build_unit(args.book, unit_no)
        if not sheet:
            print(f"{unit_no:2}과 지침서 색인에 없음")
            continue
        save_sheet(sheet)
        print(f"{unit_no:2}과 {sheet.title} — 문법 {len(sheet.grammar)} · 어휘 {len(sheet.vocabulary)} {'· ' + ', '.join(sheet.notes[:-1]) if len(sheet.notes) > 1 else ''}")
