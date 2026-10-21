"""
이 파일의 역할: 단원 시트 목록 (화면의 교재·과 고르기, 기술 ADR-0032).

  GET /curriculum → {books: [{id, title, units: [{unit_no, title, status}]}]}
"""

from fastapi import APIRouter

from app.curriculum.sheets import BOOK_SOURCES, list_units

router = APIRouter(tags=["curriculum"])


@router.get("/curriculum")
def curriculum() -> dict:
    return {"books": [{"id": book, "title": info["title"], "units": list_units(book)} for book, info in BOOK_SOURCES.items()]}
