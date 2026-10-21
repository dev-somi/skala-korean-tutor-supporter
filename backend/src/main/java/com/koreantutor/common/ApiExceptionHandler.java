package com.koreantutor.common;

import com.koreantutor.aiclient.AiServerException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;
import java.util.stream.Collectors;

/** 오류 응답 모양: {code, message, retryable} — SSE error 이벤트와 같다. */
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    ResponseEntity<Map<String, Object>> notFound(NotFoundException e) {
        return body(HttpStatus.NOT_FOUND, "NOT_FOUND", e.getMessage(), false);
    }

    @ExceptionHandler(ConflictException.class)
    ResponseEntity<Map<String, Object>> conflict(ConflictException e) {
        return body(HttpStatus.CONFLICT, "CONFLICT", e.getMessage(), false);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    ResponseEntity<Map<String, Object>> badRequest(IllegalArgumentException e) {
        return body(HttpStatus.BAD_REQUEST, "BAD_REQUEST", e.getMessage(), false);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<Map<String, Object>> invalid(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(f -> f.getField() + ": " + f.getDefaultMessage())
                .collect(Collectors.joining(", "));
        return body(HttpStatus.BAD_REQUEST, "VALIDATION_ERROR", message, false);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<Map<String, Object>> unreadable(HttpMessageNotReadableException e) {
        return body(HttpStatus.BAD_REQUEST, "INVALID_JSON", e.getMostSpecificCause().getMessage(), false);
    }

    @ExceptionHandler(AiServerException.class)
    ResponseEntity<Map<String, Object>> aiServer(AiServerException e) {
        return body(HttpStatus.BAD_GATEWAY, e.getCode(), e.getMessage(), e.isRetryable());
    }

    private static ResponseEntity<Map<String, Object>> body(HttpStatus status, String code, String message, boolean retryable) {
        return ResponseEntity.status(status).body(Map.of("code", code, "message", String.valueOf(message), "retryable", retryable));
    }
}
