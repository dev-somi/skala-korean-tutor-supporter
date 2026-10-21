"""
이 파일의 역할: 만들어진 PPT/PDF 내려받기.  GET /files/{output/ 기준 상대 경로}
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.agent.lesson_prep import pptx_builder

router = APIRouter(tags=["files"])
ALLOWED_SUFFIXES = {".pptx", ".pdf"}


@router.get("/files/{file_path:path}")
def download(file_path: str):
    root = pptx_builder.OUTPUT_DIR.resolve()
    path = (root / file_path).resolve()
    # output/ 밖의 파일이나 PPT/PDF가 아닌 파일(checkpoints.db 등)은 내주지 않는다
    if not path.is_relative_to(root) or path.suffix not in ALLOWED_SUFFIXES or not path.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(path, filename=path.name)
