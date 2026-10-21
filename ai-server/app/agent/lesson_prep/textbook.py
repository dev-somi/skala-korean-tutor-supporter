"""
이 파일의 역할: 교재 JSON을 다루는 작은 도우미 함수 모음.

- 교재 파일 읽기
- 한 과 안의 모든 항목을 "ID -> 항목" 형태로 모으기
- 항목 하나를 사람이 읽을 수 있는 글(줄 목록)로 바꾸기

교재 내용은 절대 바꾸지 않고, 읽어서 그대로 보여주기만 한다.
"""

import json
import os
from pathlib import Path

from app.agent.lesson_prep.schemas import TextbookUnit

# 데이터 폴더 위치. 테스트에서는 DATA_DIR 환경변수로 다른 폴더를 가리킬 수 있다.
PROJECT_DIR = Path(__file__).resolve().parents[3]  # ai-server/


def get_data_dir() -> Path:
    """데이터 폴더 경로를 돌려준다. (기본: 프로젝트의 data/ 폴더)"""
    return Path(os.environ.get("DATA_DIR", PROJECT_DIR / "data"))


def load_unit(unit_no: int) -> dict:
    """과 번호에 해당하는 교재 JSON을 읽고, 형식을 검사한 뒤 dict로 돌려준다."""
    path = get_data_dir() / "textbook" / f"unit_{unit_no:02d}.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # pydantic으로 형식을 검사한다. 형식이 틀리면 여기서 에러가 난다.
    unit = TextbookUnit.model_validate(data)
    return unit.model_dump()


def collect_items(unit: dict) -> dict:
    """
    한 과 안의 모든 항목을 {ID: 항목} dict로 모은다.
    항목마다 종류를 알 수 있도록 "kind"와, 몇 과인지 알 수 있도록 "unit_no"를 붙인다.
    """
    items = {}
    # (교재 JSON의 키, 항목에 붙일 종류 이름) 쌍
    kinds = [
        ("vocabulary", "vocab"),
        ("grammar", "grammar"),
        ("dialogues", "dialogue"),
        ("readings", "reading"),
        ("exercises", "exercise"),
    ]
    for key, kind in kinds:
        for item in unit[key]:
            # 원본 dict를 건드리지 않도록 복사본에 정보를 덧붙인다
            items[item["id"]] = {**item, "kind": kind, "unit_no": unit["unit_no"]}
    return items


def all_items_by_id(state: dict) -> dict:
    """이번 과의 항목 + 과거에 배운 항목을 합쳐 {ID: 항목} dict로 돌려준다."""
    items = collect_items(state["textbook_unit"])
    for item in state.get("past_items", []):
        items[item["id"]] = item
    return items


def format_item(item: dict) -> list[str]:
    """교재 항목 하나를 화면/PPT/프롬프트에 쓸 수 있는 줄 목록으로 바꾼다. (원문 그대로)"""
    kind = item["kind"]

    if kind == "vocab":
        lines = [f"{item['word']} ({item['pos']}) : {item['meaning']}"]
        if item["example"]:
            lines.append(f"   예) {item['example']}")
        return lines

    if kind == "grammar":
        lines = [f"문법: {item['form']}"]
        for example in item["examples"]:
            lines.append(f"   예) {example}")
        return lines

    if kind == "dialogue":
        return [f"{line['speaker']}: {line['text']}" for line in item["lines"]]

    if kind == "reading":
        return [item["text"]]

    # 남은 종류는 연습문제(exercise)
    return [item["instruction"]] + [f"   {q}" for q in item["questions"]]


def format_item_for_prompt(item: dict) -> str:
    """LLM 프롬프트에 넣을 때 쓰는 형식: ID와 페이지를 앞에 붙인다."""
    lines = format_item(item)
    # 문법은 교재 설명도 LLM이 알아야 하므로 함께 넣는다
    if item["kind"] == "grammar":
        lines.insert(1, f"   교재 설명: {item['description']}")
    return f"[{item['id']}] (p.{item['page']}) " + "\n".join(lines)


def load_all_items() -> dict:
    """교재 폴더의 모든 과를 읽어 {ID: 항목} dict로 돌려준다. (교재 ID 존재 검사용)"""
    items = {}
    for path in sorted((get_data_dir() / "textbook").glob("unit_*.json")):
        items.update(collect_items(load_unit(int(path.stem.split("_")[1]))))
    return items
