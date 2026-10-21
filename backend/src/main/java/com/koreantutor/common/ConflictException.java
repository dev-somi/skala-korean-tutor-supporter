package com.koreantutor.common;

/** 지금 상태에서는 할 수 없는 요청 (예: 검토 대기가 아닌 수업에 검토 결과를 보냄) */
public class ConflictException extends RuntimeException {
    public ConflictException(String message) {
        super(message);
    }
}
