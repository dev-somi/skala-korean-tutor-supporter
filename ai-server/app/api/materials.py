"""
이 파일의 역할: 출처로 찾은 교재 원본 PDF를 선생님 컴퓨터에서 그 쪽으로 연다. (기술 ADR-0030)

  GET  /materials       → 원본 PDF가 등록된 책 ID 목록 (화면이 "원문 열기" 버튼을 보일지 정한다)
  POST /materials/open  {book, page} → {opened, page, message?}
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.rag import pdfs

router = APIRouter(tags=["materials"])


class OpenRequest(BaseModel):
    book: str
    page: int  # 출처에 적힌 쪽 (책에 인쇄된 쪽)


@router.get("/materials")
def materials() -> dict:
    return {"books": pdfs.available()}


@router.post("/materials/open")
def open_material(body: OpenRequest) -> dict:
    # 등록부에 있는 책만 연다. 경로는 받지 않는다
    return pdfs.open_pdf(body.book, body.page)
