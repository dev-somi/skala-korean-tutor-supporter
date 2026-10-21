"""
이 파일의 역할: 구조화 로그(JSON 한 줄). 필드 이름은 student_id, lesson_id, thread_id로 고정한다 (참고노트 6장).
사용: logger.info("...", extra={"thread_id": tid})
"""

import json
import logging

FIELDS = ("student_id", "lesson_id", "thread_id")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "service": "ai-server",
        }
        for field in FIELDS:
            if hasattr(record, field):
                data[field] = getattr(record, field)
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("ai_server")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False
