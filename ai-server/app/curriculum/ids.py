"""
이 파일의 역할: 옛 교재 항목 ID(u02-g01)를 단원 시트 ID(표준 ID)로 바꾼다. (기술 ADR-0032)

  문법 u02-g01 → 대응표(textbook_map.json)의 첫 표준 ID (단원 시트의 문법 ID와 같다)
  어휘 u02-v05 → 같은 낱말의 표준 어휘 ID, 표준 목록에 없으면 표현 ID (ko1-u02-x01, 시트와 같은 규칙)
  대화·읽기·연습 u02-d01 → ko1-u02-d01
  이미 새 ID면 그대로

DB 이전(Flyway)과, 이전 전에 들어오는 옛 ID를 읽을 때 같이 쓴다.
"""

import re
from functools import lru_cache

from app.curriculum.convert_textbook import BOOK, convert, textbook_units

OLD_ID = re.compile(r"^u\d{2}-[vgdre]\d{2}$")


@lru_cache
def old_to_new() -> dict[str, str]:
    """{옛 교재 ID: 새 ID}. 손으로 만든 교재 JSON을 시트로 바꿀 때의 ID 규칙을 그대로 쓴다 (convert_textbook)."""
    from app.agent.lesson_prep.textbook import load_unit

    table = {}
    for unit_no in textbook_units():
        old, new = load_unit(unit_no), convert(unit_no).model_dump()
        for kind in ("vocabulary", "grammar", "dialogues", "readings", "exercises"):
            for before, after in zip(old[kind], new[kind]):
                table[before["id"]] = after["id"]
    return table


def to_new(item_id: str | None) -> str | None:
    if item_id is None or not OLD_ID.match(item_id):
        return item_id
    return old_to_new().get(item_id, f"{BOOK}-{item_id}")
