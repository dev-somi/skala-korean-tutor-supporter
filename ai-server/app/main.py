"""
이 파일의 역할: FastAPI 앱의 진입점.

그래프·checkpointer처럼 만들기 비싼 객체는 lifespan에서 한 번만 만들고
요청마다 app.state에서 꺼내 쓴다 (참고노트 3-1).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.lesson_prep.graph import build_graph
from app.agent.post_lesson.graph import build_graph as build_post_lesson_graph
from app.api import curriculum, files, grammar_qa, intake, level_test, materials, post_lesson, prep, report, standard, textbook, traces
from app.logging_config import setup_logging
from app.persistence.checkpointer import create_checkpointer

setup_logging()
logger = logging.getLogger("ai_server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with create_checkpointer() as saver:
        app.state.prep_graph = build_graph(saver)
        app.state.post_lesson_graph = build_post_lesson_graph()
        logger.info("ai-server ready")
        yield


app = FastAPI(title="ai-server", lifespan=lifespan)
app.include_router(intake.router)
app.include_router(prep.router)
app.include_router(post_lesson.router)
app.include_router(files.router)
app.include_router(level_test.router)
app.include_router(report.router)
app.include_router(standard.router)
app.include_router(textbook.router)
app.include_router(grammar_qa.router)
app.include_router(traces.router)
app.include_router(materials.router)
app.include_router(curriculum.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
