"""
이 파일의 역할: 자동으로 만든 단원 시트 초안을 사람이 만든 시트(정답)와 비교한다. (기술 ADR-0032)

  uv run python -m app.curriculum.evaluate ko1

비교는 표준 ID로 한다 (문법: standard_ids 전부, 어휘: 표준 목록에 있는 낱말만 — 표현은 진도에 세지 않는다).
  정밀도 = 초안이 뽑은 것 중 정답에 있는 비율 (틀린 걸 넣었나)
  재현율 = 정답 중 초안이 뽑은 비율 (빠뜨렸나)
"""

import sys

from app.curriculum.build import build_unit
from app.curriculum.convert_textbook import convert, textbook_units


def ids(sheet: dict, kind: str) -> set[str]:
    if kind == "grammar":
        return {sid for g in sheet["grammar"] for sid in g["standard_ids"]}
    return {v["id"] for v in sheet["vocabulary"] if v["id"].startswith("std-")}


def compare(book: str, unit_no: int) -> dict:
    gold = convert(unit_no).model_dump()
    draft = build_unit(book, unit_no).model_dump()
    result = {}
    for kind in ("grammar", "vocab"):
        g, d = ids(gold, kind), ids(draft, kind)
        hit = g & d
        result[kind] = {
            "precision": len(hit) / len(d) if d else None,
            "recall": len(hit) / len(g) if g else None,
            "missing": sorted(g - d),
            "extra": sorted(d - g),
        }
    return result


if __name__ == "__main__":
    book = sys.argv[1] if len(sys.argv) > 1 else "ko1"
    for unit_no in textbook_units():
        for kind, v in compare(book, unit_no).items():
            print(f"{unit_no}과 {kind:7} 정밀도 {v['precision']:.0%} 재현율 {v['recall']:.0%}  빠짐 {v['missing']}  더 뽑음 {v['extra']}")
    print("(정답: 손으로 만든 교재 JSON. 대화·연습은 아직 비교하지 않는다)")
