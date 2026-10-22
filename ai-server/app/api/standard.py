"""
이 파일의 역할: 국립국어원 표준 교육과정 등급 목록 찾아보기 API (기획 ADR-0016).

  GET /standard/grammar?level=&category=&q=          문법·표현 (336개, 한 번에 돌려준다)
  GET /standard/vocab?level=&pos=&q=&offset=&limit=   어휘 (10,635개라 나눠서 돌려준다)

문법·어휘 항목에는 그 항목을 다루는 교재 과를 붙인다. 선생님이 "이 문법을 교재 몇 과에서 배우나"를 볼 수 있게.
교재 과는 단원 시트(data/curriculum/<book>/unit_NN.json)의 표준 ID에서 거꾸로 찾는다 (기술 ADR-0036).
"""

import json
from collections import Counter
from functools import lru_cache

from fastapi import APIRouter, Query

from app.agent.lesson_prep.textbook import get_data_dir
from app.curriculum import sheets
from app.standard.levels import POS_LIST, grammar_items, pos_parts, vocab_items

router = APIRouter(tags=["standard"])


def _textbook_links() -> dict[str, list[dict]]:
    """
    {표준 ID: [{book, title, short, unit_no, status}]} — 단원 시트를 거꾸로 읽는다. 문법은 standard_ids, 어휘는 id.
    시트 파일 읽기는 sheets.all_sheets가 수정 시각으로 캐시하므로, build로 시트를 다시 만들면 바로 반영된다.
    """
    links: dict[str, list[dict]] = {}
    for sheet in sheets.all_sheets():
        info = sheets.BOOK_SOURCES.get(sheet["book"], {})
        link = {
            "book": sheet["book"],
            "title": info.get("title", sheet["book"]),
            "short": info.get("short", sheet["book"]),
            "unit_no": sheet["unit_no"],
            "status": sheet["status"],
        }
        ids = [sid for g in sheet["grammar"] for sid in (g.get("standard_ids") or [g["id"]])]
        ids += [v["id"] for v in sheet["vocabulary"]]
        for sid in dict.fromkeys(ids):  # 한 과에 같은 ID가 두 번 있어도 한 번만
            if sid.startswith("std-"):
                links.setdefault(sid, []).append(link)
    return links


@lru_cache
def _repeated() -> tuple[set[str], set[str]]:
    """목록에 두 번 이상 나오는 (문법 대표형, 어휘 글자). 동음이의어 번호는 이때만 보여 준다"""
    def twice(values: list[str]) -> set[str]:
        return {v for v, n in Counter(values).items() if n > 1}

    return twice([g["form"] for g in grammar_items()]), twice([v["word"] for v in vocab_items()])


def _source() -> dict:
    return json.loads((get_data_dir() / "standard" / "grammar.json").read_text(encoding="utf-8"))["source"]


def _match(text: str | None, *fields: str | None) -> bool:
    return not text or any(text in (f or "") for f in fields)


# 원본 엑셀의 "분류" 칸 값 (형태 기준: 학교문법의 조사·어미 + 덩어리 "표현"). 화면에 보여 줄 순서
CATEGORIES = ["조사", "선어말어미", "연결어미", "종결어미", "전성어미", "표현"]


@router.get("/standard/grammar")
def standard_grammar(
    level: int | None = Query(default=None, ge=1, le=6),
    category: str | None = Query(default=None, max_length=10),
    q: str | None = Query(default=None, max_length=50),
) -> dict:
    links = _textbook_links()
    q = (q or "").strip()
    # 분류별 개수는 분류 필터를 걸기 전 (등급·검색어만 적용) 기준이다. 다른 분류로 바꾸면 몇 개가 나올지 보이게
    matched = [g for g in grammar_items() if (level is None or g["level"] == level) and _match(q, g["form"], g["meaning"], *g["related"])]
    counts = {c: sum(1 for g in matched if g["category"] == c) for c in CATEGORIES}
    repeated = _repeated()[0]
    items = [
        {**g, "textbook": links.get(g["id"], []), "has_homonyms": g["form"] in repeated}
        for g in matched
        if not category or g["category"] == category
    ]
    return {"source": _source(), "total": len(items), "categories": counts, "items": items}


@router.get("/standard/vocab")
def standard_vocab(
    level: int | None = Query(default=None, ge=1, le=6),
    pos: str | None = Query(default=None, max_length=20),
    q: str | None = Query(default=None, max_length=50),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    q = (q or "").strip()
    matched = [v for v in vocab_items() if (level is None or v["level"] == level) and _match(q, v["word"], v["guide"])]
    # 품사별 개수는 품사 필터를 걸기 전 (등급·검색어 기준). 품사가 둘인 단어("부사/명사")는 양쪽에 다 센다
    pos_counts = {p: sum(1 for v in matched if p in pos_parts(v["pos"])) for p in POS_LIST}
    found = [v for v in matched if not pos or pos in pos_parts(v["pos"])]
    # 검색어와 글자가 같은 단어를 먼저 보여 준다 ("가다"를 찾으면 "가다"가 "가다듬다"보다 앞)
    if q:
        found.sort(key=lambda v: (v["word"] != q, not v["word"].startswith(q), v["level"]))
    repeated = _repeated()[1]
    links = _textbook_links()
    page = [{**v, "textbook": links.get(v["id"], []), "has_homonyms": v["word"] in repeated} for v in found[offset : offset + limit]]
    return {"source": _source(), "total": len(found), "all_total": len(matched), "pos_counts": pos_counts, "offset": offset, "items": page}
