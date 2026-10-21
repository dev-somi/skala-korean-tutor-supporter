"""
이 파일의 역할: 문법별·모국어별 지식(자주 틀리는 점, 예상 질문, 설명 팁)을 데이터에서 꺼낸다. (기술 ADR-0022)

  data/standard/l1_notes.json   키 = 국립국어원 표준 항목 ID. Claude 초안 + 선생님 검수(reviewed)

교재 항목 ID(u03-g02) → textbook_map → 표준 ID(std-g-007) → 노트 순서로 찾는다.
작은 로컬 모델이 지어내던 지식을 검수된 데이터로 바꾸기 위한 것이다 (ADR-0020).
"""

import json
from functools import lru_cache

from app.agent.lesson_prep.textbook import get_data_dir
from app.standard.levels import standard_ids


@lru_cache
def _notes() -> list[dict]:
    path = get_data_dir() / "standard" / "l1_notes.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["notes"]


def notes_for_item(textbook_item_id: str) -> list[dict]:
    """
    교재 문법 항목 하나에 맞는 노트들. 표준 ID가 하나라도 겹치면 맞는 것으로 본다.
    어휘로 이어진 구문 노트(예: 이/가 아니다 → std-v 아니다)가 있으면 그것만 쓴다.
    "이/가 아니다"가 "이/가" 노트까지 함께 끌어오지 않게 하려는 것이다.
    """
    ids = set(standard_ids(textbook_item_id))
    matched = [note for note in _notes() if ids & set(note["std_ids"])]
    constructions = [note for note in matched if any(i.startswith("std-v-") for i in note["std_ids"])]
    return constructions or matched


def lookup(textbook_item_ids: list[str], lang: str) -> tuple[list[dict], list[str]]:
    """
    수업의 문법 항목들에 대한 노트를 모은다.
    돌려주는 값: (노트 목록 — 같은 노트는 한 번만, 노트가 없는 교재 항목 ID 목록)
    노트 하나 = {form, reviewed, common_mistakes, expected_qa, explain_tip}
    """
    found, seen, missing = [], set(), []
    for item_id in textbook_item_ids:
        notes = [note for note in notes_for_item(item_id) if lang in note]
        if not notes:
            missing.append(item_id)
        for note in notes:
            if note["form"] in seen:
                continue
            seen.add(note["form"])
            found.append({"form": note["form"], **note[lang]})
    return found, missing


def notes_for_keys(keys: set[str], lang: str) -> list[dict]:
    """형태 키로 모국어 노트를 찾는다 (문법 질문용, 기술 ADR-0025). 노트의 form("이/가")에서 키를 만든다.
    노트 하나 = {form, reviewed, common_mistakes, expected_qa, explain_tip}"""
    from app.rag.forms import form_keys  # 순환 import 방지

    return [{"form": note["form"], **note[lang]} for note in _notes() if keys & form_keys(note["form"]) and lang in note]
