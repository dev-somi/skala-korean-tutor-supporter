"""
이 파일의 역할: 단원 시트를 읽고 쓴다. (기술 ADR-0032)

  data/curriculum/<book>/unit_NN.json
"""

import json
from functools import lru_cache
from pathlib import Path

from app.agent.lesson_prep.textbook import get_data_dir
from app.curriculum.schemas import UnitSheet

# 교재 시리즈 → 그 과의 근거를 찾는 색인 책 (지침서·본책·익힘책)
BOOK_SOURCES = {
    "ko1": {"title": "세종학당 한국어 1", "guide": "ko1_guide", "textbook": "ko1_textbook", "workbook": "ko1_workbook"},
    "ko2": {"title": "세종학당 한국어 2", "guide": "ko2_guide", "textbook": "ko2_textbook", "workbook": "ko2_workbook"},
}


def sheet_dir(book: str) -> Path:
    return get_data_dir() / "curriculum" / book


def sheet_path(book: str, unit_no: int) -> Path:
    return sheet_dir(book) / f"unit_{unit_no:02d}.json"


def load_sheet(book: str, unit_no: int) -> dict | None:
    path = sheet_path(book, unit_no)
    if not path.exists():
        return None
    return UnitSheet.model_validate_json(path.read_text(encoding="utf-8")).model_dump()


def save_sheet(sheet: UnitSheet) -> Path:
    path = sheet_path(sheet.book, sheet.unit_no)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sheet.model_dump(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def list_units(book: str) -> list[dict]:
    """그 교재의 단원 시트 목록 (화면의 과 고르기)"""
    units = []
    for path in sorted(sheet_dir(book).glob("unit_*.json")):
        sheet = UnitSheet.model_validate_json(path.read_text(encoding="utf-8"))
        units.append({"unit_no": sheet.unit_no, "title": sheet.title, "status": sheet.status})
    return units


@lru_cache(maxsize=512)
def _read(path: Path, mtime: float) -> dict:
    """파일 하나를 읽는다. 수정 시각이 키라서 build로 다시 만들면 새로 읽는다."""
    return UnitSheet.model_validate_json(path.read_text(encoding="utf-8")).model_dump()


def all_sheets() -> list[dict]:
    """모든 교재의 단원 시트 (BOOK_SOURCES 순서 → 과 순서). 호출마다 파일 40여 개를 다시 파싱하지 않게 캐시한다."""
    return [_read(path, path.stat().st_mtime) for book in BOOK_SOURCES for path in sorted(sheet_dir(book).glob("unit_*.json"))]
