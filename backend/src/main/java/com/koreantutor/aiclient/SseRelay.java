package com.koreantutor.aiclient;

import com.koreantutor.config.AppProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import reactor.core.Disposable;
import reactor.core.publisher.Flux;
import reactor.core.scheduler.Schedulers;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

/**
 * ai-server SSE를 받아 브라우저 SseEmitter로 그대로 다시 보낸다 (ADR-0006).
 * 이벤트마다 onEvent를 먼저 부르므로, done 이벤트를 받으면 DB에 저장한 뒤 브라우저에 전달된다.
 */
@Component
public class SseRelay {

    private static final Logger log = LoggerFactory.getLogger(SseRelay.class);

    private final Duration timeout;
    private final tools.jackson.databind.json.JsonMapper jsonMapper;

    public SseRelay(AppProperties props, tools.jackson.databind.json.JsonMapper jsonMapper) {
        this.timeout = props.aiServer().sseTimeout();
        this.jsonMapper = jsonMapper;
    }

    /**
     * @param source     ai-server 이벤트 스트림
     * @param onEvent    이벤트 하나를 받을 때마다 (브라우저로 보내기 전에) 실행. 두 번째 인자는 스트림 시작부터 지난 시간
     * @param onFinished 스트림이 끝나면(성공·실패 모두) 걸린 시간과 함께 실행 — AI 대기 시간 기록용
     */
    public SseEmitter relay(Flux<ServerSentEvent<String>> source,
                            BiConsumer<ServerSentEvent<String>, Duration> onEvent,
                            Consumer<Duration> onFinished) {
        SseEmitter emitter = new SseEmitter(timeout.toMillis());
        Instant started = Instant.now();

        Disposable subscription = source
                // DB 저장(블로킹)을 하므로 네트워크 스레드가 아닌 곳에서 처리한다
                .publishOn(Schedulers.boundedElastic())
                .doFinally(signal -> onFinished.accept(Duration.between(started, Instant.now())))
                .subscribe(
                        event -> {
                            try {
                                onEvent.accept(event, Duration.between(started, Instant.now()));
                                emitter.send(SseEmitter.event().name(event.event()).data(event.data()));
                            } catch (IOException e) {
                                throw new AlreadyHandled(e); // 브라우저가 끊김: 보낼 곳이 없다
                            } catch (RuntimeException e) {
                                log.error("failed to handle ai-server event {}", event.event(), e);
                                sendError(emitter, "EVENT_HANDLING_ERROR", e.getMessage(), false);
                                throw new AlreadyHandled(e);
                            }
                        },
                        error -> {
                            if (!(error instanceof AlreadyHandled)) {
                                log.warn("ai-server stream failed", error);
                                boolean retryable = !(error instanceof WebClientResponseException r) || r.getStatusCode().is5xxServerError();
                                sendError(emitter, "AI_SERVER_ERROR", describe(error), retryable);
                            }
                            emitter.complete();
                        },
                        emitter::complete);

        // 브라우저가 끊거나 시간이 지나면 ai-server 구독도 끊는다
        emitter.onCompletion(subscription::dispose);
        emitter.onTimeout(subscription::dispose);
        emitter.onError(e -> subscription.dispose());
        return emitter;
    }

    /** Spring이 직접 만든 이벤트 하나만 보내고 끝내는 SseEmitter (예: 시작 전 검증 실패) */
    public void sendError(SseEmitter emitter, String code, String message, boolean retryable) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("code", code);
        data.put("message", message);
        data.put("retryable", retryable);
        try {
            emitter.send(SseEmitter.event().name("error").data(jsonMapper.writeValueAsString(data)));
        } catch (IOException | RuntimeException ignored) {
            // 브라우저가 이미 끊겼으면 보낼 곳이 없다
        }
    }

    private static String describe(Throwable error) {
        if (error instanceof WebClientResponseException r) {
            return r.getStatusCode() + " " + r.getResponseBodyAsString();
        }
        return error.getClass().getSimpleName() + ": " + error.getMessage();
    }

    /** 이미 처리(또는 보고)한 오류. error 콜백에서 error 이벤트를 한 번 더 보내지 않게 표시한다. */
    private static final class AlreadyHandled extends RuntimeException {
        AlreadyHandled(Throwable cause) {
            super(cause);
        }
    }
}
