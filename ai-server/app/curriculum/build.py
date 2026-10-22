"""
이 파일의 역할: 색인된 자료에서 단원 시트 초안(status: draft)을 만든다. (기술 ADR-0032)

  uv run python -m app.curriculum.build ko1              # 지침서에 있는 과 전부
  uv run python -m app.curriculum.build ko1 --units 5-9
  uv run python -m app.curriculum.build ko3a             # 3A~6B: 본책에 있는 과 전부

- 문법·어휘는 코드 규칙으로 뽑는다. LLM은 쓰지 않는다.
  1·2권은 지침서에서 (app.curriculum.extract), 3A~6B는 본책에서 (app.curriculum.textbook_extract, 기술 ADR-0040).
- 선생님이 검수한 시트(status: reviewed)는 덮어쓰지 않는다.
- 대화·읽기·연습은 본책·익힘책 OCR 쪽에서 코드 규칙으로 (app.curriculum.materials). 연습은 숙제에 쓰이므로 익힘책을 앞에 둔다.
"""

import argparse

from app.curriculum import extract, materials, textbook_extract
from app.curriculum.schemas import SheetDialogue, SheetExercise, SheetGrammar, SheetReading, SheetVocab, Source, UnitSheet
from app.curriculum.sheets import BOOK_SOURCES, load_sheet, save_sheet

MIN_GRAMMAR = 1  # 이보다 적게 뽑히면 notes에 적는다
MIN_VOCAB = 5


def build_unit(book: str, unit_no: int) -> UnitSheet | None:
    if BOOK_SOURCES[book]["extract"] == "textbook":
        return build_textbook_unit(book, unit_no)
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

    textbook = BOOK_SOURCES[book]["textbook"]
    dialogues, readings, exercises = unit_materials(book, unit_no, materials.unit_pages(textbook, unit_no), materials.script_dialogues(textbook, unit_no))

    if len(grammar) < MIN_GRAMMAR:
        notes.append("지침서에서 문법을 찾지 못함")
    if len(vocabulary) < MIN_VOCAB:
        notes.append(f"지침서에서 어휘를 {len(vocabulary)}개만 찾음")
    if not dialogues:
        notes.append("본책 부록에서 듣기 대화를 찾지 못함")
    if not exercises:
        notes.append("익힘책·본책에서 연습을 찾지 못함")
    notes.append("대화·연습은 OCR 글이라 빈칸·보기가 섞여 있을 수 있음 (원문 쪽을 함께 확인)")
    return UnitSheet(
        book=book,
        unit_no=unit_no,
        title=extract.unit_titles(guide).get(unit_no, f"{unit_no}과"),
        status="draft",
        page_start=pages[0],
        page_end=pages[-1],
        vocabulary=vocabulary,
        grammar=grammar,
        dialogues=dialogues,
        readings=readings,
        exercises=exercises,
        notes=notes,
    )


def unit_materials(book: str, unit_no: int, textbook_pages: list[dict], scripts: list[dict]) -> tuple[list, list, list]:
    """대화·읽기·연습 (본책·익힘책 OCR 쪽). 연습은 숙제에 쓰이므로 익힘책을 앞에 둔다."""
    prefix = f"{book}-u{unit_no:02d}"
    dialogues = [
        SheetDialogue(id=f"{prefix}-d{i:02d}", lines=d["lines"], page=d["page"], source=Source(book=d["book"], pages=[d["page"]]))
        for i, d in enumerate(scripts, 1)
    ]
    readings = [
        SheetReading(id=f"{prefix}-r{i:02d}", text=r["text"], page=r["page"], source=Source(book=r["book"], pages=[r["page"]]))
        for i, r in enumerate(materials.readings(textbook_pages), 1)
    ]
    found = materials.exercises(materials.unit_pages(BOOK_SOURCES[book]["workbook"], unit_no)) + materials.exercises(textbook_pages)
    exercises = [
        SheetExercise(id=f"{prefix}-e{i:02d}", instruction=e["instruction"], questions=e["questions"], page=e["page"], source=Source(book=e["book"], pages=[e["page"]]))
        for i, e in enumerate(found, 1)
    ]
    return dialogues, readings, exercises


def build_textbook_unit(book: str, unit_no: int) -> UnitSheet | None:
    """3A~6B: 본책 쪽에서 문법(문형)·어휘를 뽑는다 (기술 ADR-0040). 출처는 본책 쪽."""
    textbook = BOOK_SOURCES[book]["textbook"]
    pages = textbook_extract.unit_pages(textbook, unit_no)
    if not pages:
        return None
    page_nos = [p["page"] for p in pages]
    notes = []

    grammar = []
    for item in textbook_extract.grammar_items(pages):
        page_no = item["page"]["page"] if item["page"] else page_nos[0]  # 학습목표에만 나온 문법(부가 문법)은 과 첫 쪽
        grammar.append(
            SheetGrammar(
                id=item["standard_ids"][0],
                standard_ids=item["standard_ids"],
                form=item["form"],
                description=textbook_extract.grammar_description(item["page"]),
                examples=textbook_extract.grammar_examples(item["form"], item["page"]),
                page=page_no,
                level=item["level"],
                source=Source(book=textbook, pages=[page_no]),
            )
        )

    vocabulary, seen, n_expr = [], set(), 0
    for entry, example, page in textbook_extract.vocab_entries(pages):
        for word, std in textbook_extract.lookup_words(entry):
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
                    word=word if std else entry,
                    pos=std["pos"] if std else "",
                    example=example,
                    page=page["page"],
                    level=std["level"] if std else None,
                    source=Source(book=textbook, pages=[page["page"]]),
                )
            )

    # 본책 쪽 모양({page, text})을 materials가 읽는 parent 모양으로
    textbook_pages = [{"text": p["text"], "pages": [p["page"]], "book": textbook} for p in pages]
    dialogues, readings, exercises = unit_materials(book, unit_no, textbook_pages, [])

    if len(grammar) < MIN_GRAMMAR:
        notes.append("본책에서 문법을 찾지 못함")
    if len(vocabulary) < MIN_VOCAB:
        notes.append(f"본책에서 어휘를 {len(vocabulary)}개만 찾음")
    if not exercises:
        notes.append("익힘책·본책에서 연습을 찾지 못함")
    notes.append("문법·어휘는 본책 OCR에서 코드 규칙으로 뽑음. 대화는 아직 뽑지 않음 (원문 쪽을 함께 확인)")
    return UnitSheet(
        book=book,
        unit_no=unit_no,
        title=textbook_extract.unit_titles(textbook).get(unit_no, f"{unit_no}과"),
        status="draft",
        page_start=page_nos[0],
        page_end=page_nos[-1],
        vocabulary=vocabulary,
        grammar=grammar,
        dialogues=dialogues,
        readings=readings,
        exercises=exercises,
        notes=notes,
    )


def parse_units(text: str | None, book: str) -> list[int]:
    if not text:
        if BOOK_SOURCES[book]["extract"] == "textbook":
            return sorted(textbook_extract.unit_titles(BOOK_SOURCES[book]["textbook"]))
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
            print(f"{unit_no:2}과 색인에 없음")
            continue
        save_sheet(sheet)
        warnings = ", ".join(sheet.notes[:-1])
        print(f"{unit_no:2}과 {sheet.title} — 문법 {len(sheet.grammar)} · 어휘 {len(sheet.vocabulary)} · 대화 {len(sheet.dialogues)} · 읽기 {len(sheet.readings)} · 연습 {len(sheet.exercises)} {'· ' + warnings if warnings else ''}")
