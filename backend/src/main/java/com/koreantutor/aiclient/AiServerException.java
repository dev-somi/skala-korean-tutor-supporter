package com.koreantutor.aiclient;

/** ai-server 호출 실패. retryable이면 프론트가 [다시 시도]를 보여 준다. */
public class AiServerException extends RuntimeException {

    private final String code;
    private final boolean retryable;

    public AiServerException(String code, String message, boolean retryable, Throwable cause) {
        super(message, cause);
        this.code = code;
        this.retryable = retryable;
    }

    public String getCode() { return code; }
    public boolean isRetryable() { return retryable; }
}
