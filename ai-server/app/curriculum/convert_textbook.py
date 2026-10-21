"""
이 파일의 역할: 손으로 만든 교재 JSON(data/textbook/unit_NN.json, 「한국어 1」)을 단원 시트(status: reviewed)로 바꾼다. (기술 ADR-0032)

  uv run python -m app.curriculum.convert_textbook

- 문법 ID: 교재 ID → 대응표(data/standard/textbook_map.json)의 표준 ID. 첫 번째가 시트 ID, 전부는 standard_ids
- 어휘 ID: 표준 목록에 같은 낱말이 있으면 표준 ID, 없으면 표현(ko1-uNN-xNN)
- 대화·읽기·연습: ko1-u02-d01처럼 책 이름을 붙인다
교재 JSON은 사람이 검수한 데이터라 자동 초안의 정확도를 재는 정답으로도 쓴다 (app.curriculum.evaluate).
"""

from app.agent.lesson_prep.textbook import get_data_dir, load_unit
from app.curriculum.extract import standard_vocab
from app.curriculum.schemas import UnitSheet
from app.curriculum.sheets import save_sheet
from app.standard.levels import get_item, standard_ids

BOOK = "ko1"
TEXTBOOK_BOOK = "ko1_textbook"  # 교재 JSON의 쪽 = 본책 쪽


def convert(unit_no: int) -> UnitSheet:
    unit = load_unit(unit_no)

    def src(page: int) -> dict:
        return {"book": TEXTBOOK_BOOK, "pages": [page]}

    def local(item_id: str) -> str:
        return f"{BOOK}-{item_id}"  # u02-d01 → ko1-u02-d01

    grammar = []
    for g in unit["grammar"]:
        ids = standard_ids(g["id"])
        if not ids:
            raise ValueError(f"대응표에 없는 교재 문법: {g['id']} {g['form']}")
        levels = [get_item(i)["level"] for i in ids if get_item(i)]
        grammar.append({**g, "id": ids[0], "standard_ids": ids, "level": max(levels, default=None), "source": src(g["page"])})

    vocabulary, n_expr = [], 0
    for v in unit["vocabulary"]:
        std = standard_vocab(v["word"])
        if std:
            item_id = std["id"]
        else:
            n_expr += 1
            item_id = f"{BOOK}-u{unit_no:02d}-x{n_expr:02d}"
        vocabulary.append({**v, "id": item_id, "level": std["level"] if std else None, "pos": std["pos"] if std else v.get("pos", ""), "source": src(v["page"])})

    return UnitSheet.model_validate(
        {
            "book": BOOK,
            "unit_no": unit_no,
            "title": unit["title"],
            "status": "reviewed",
            "page_start": unit["page_start"],
            "page_end": unit["page_end"],
            "vocabulary": vocabulary,
            "grammar": grammar,
            "dialogues": [{**d, "id": local(d["id"]), "source": src(d["page"])} for d in unit["dialogues"]],
            "readings": [{**r, "id": local(r["id"]), "source": src(r["page"])} for r in unit["readings"]],
            "exercises": [{**e, "id": local(e["id"]), "source": src(e["page"])} for e in unit["exercises"]],
            "notes": ["손으로 만든 교재 JSON에서 변환 (data/textbook)"],
        }
    )


def textbook_units() -> list[int]:
    return sorted(int(p.stem.split("_")[1]) for p in (get_data_dir() / "textbook").glob("unit_*.json"))


if __name__ == "__main__":
    for unit_no in textbook_units():
        sheet = convert(unit_no)
        print(f"{unit_no}과 → {save_sheet(sheet)} (문법 {len(sheet.grammar)}, 어휘 {len(sheet.vocabulary)})")
