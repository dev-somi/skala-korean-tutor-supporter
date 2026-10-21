"""
이 파일의 역할: 기본 PPT 템플릿(templates/lesson_template.pptx)을 만든다.

템플릿은 "16:9 크기의 빈 발표 자료"다. 디자인을 바꾸고 싶으면
만들어진 lesson_template.pptx를 파워포인트에서 열어 배경/테마를 고쳐 저장하면 된다.

실행 방법: uv run python templates/make_template.py
"""

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

# 템플릿 파일이 저장될 위치 (이 스크립트와 같은 폴더)
TEMPLATE_PATH = Path(__file__).parent / "lesson_template.pptx"


def make_template() -> Path:
    """16:9 크기의 빈 템플릿 파일을 만들고 그 경로를 돌려준다."""
    prs = Presentation()  # python-pptx의 기본 발표 자료 (4:3)
    prs.slide_width = Inches(13.333)  # 16:9 가로
    prs.slide_height = Inches(7.5)  # 16:9 세로
    prs.save(str(TEMPLATE_PATH))
    return TEMPLATE_PATH


if __name__ == "__main__":
    print("템플릿을 만들었습니다:", make_template())
