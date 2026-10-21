"""
이 파일의 역할: 교재 항목 ID를 사람이 읽는 이름으로 바꿔 주는 목록 (화면 표시용, 기술 ADR-0029).

  GET /textbook/items  → {items: {ID: {kind, label, meaning, unit_no}}}

화면은 u03-v01 대신 "노래", u03-g02 대신 "을"처럼 보여 준다. 데이터 ID는 그대로 쓴다.
"""

from fastapi import APIRouter

from app.agent.lesson_prep.textbook import load_all_items

router = APIRouter(tags=["textbook"])


def label_of(item: dict) -> str:
    kind = item["kind"]
    if kind == "vocab":
        return item["word"]
    if kind == "grammar":
        return item["form"]
    if kind == "exercise":
        # "연습 Ⅰ. 대화를 완성하세요. (이/가)" → "연습 Ⅰ"
        return item["instruction"].split(".")[0].strip()
    if kind == "dialogue":
        return f"{item['unit_no']}과 대화"
    return f"{item['unit_no']}과 읽기"


@router.get("/textbook/items")
def get_items() -> dict:
    return {
        "items": {
            item_id: {"kind": item["kind"], "label": label_of(item), "meaning": item.get("meaning"), "unit_no": item["unit_no"]}
            for item_id, item in load_all_items().items()
        }
    }
