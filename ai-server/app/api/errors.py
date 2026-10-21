"""
이 파일의 역할: 예외를 "다시 시도하면 될 수도 있는 오류"와 "다시 해도 같은 오류"로 나눈다 (참고노트 4-5).
프론트는 retryable 값으로 [다시 시도] 버튼을 보여 줄지 정한다.
"""

# 이름에 이 글자가 들어간 예외는 일시적 오류로 본다 (Anthropic SDK·httpx의 타임아웃, 과부하, 연결 오류)
TRANSIENT_NAME_PARTS = ("Timeout", "RateLimit", "Overloaded", "APIConnection", "ConnectError", "InternalServer")


def error_info(exc: Exception) -> dict:
    name = type(exc).__name__
    retryable = any(part in name for part in TRANSIENT_NAME_PARTS)
    return {
        "code": "LLM_TRANSIENT_ERROR" if retryable else "GRAPH_EXECUTION_ERROR",
        "message": f"{name}: {exc}",
        "retryable": retryable,
    }
