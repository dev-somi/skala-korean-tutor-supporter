package com.koreantutor.aiclient;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Flux;
import reactor.util.retry.Retry;

import java.time.Duration;
import java.util.Map;

/**
 * ai-server(FastAPI) 호출. 요청에 필요한 데이터는 모두 여기서 담아 보낸다 (ADR-0005).
 * 요청·이벤트 모양은 ai-server/app/schemas/api.py 와 같다 (snake_case).
 */
@Component
public class AiServerClient {

    private static final ParameterizedTypeReference<ServerSentEvent<String>> SSE_TYPE = new ParameterizedTypeReference<>() {
    };
    private static final ParameterizedTypeReference<Map<String, Object>> MAP_TYPE = new ParameterizedTypeReference<>() {
    };

    // 연결 자체가 안 된 경우만 다시 시도한다 (요청이 도착했는데 실패한 것은 다시 해도 같다, 참고노트 4-5)
    private static final Retry CONNECT_RETRY = Retry.backoff(2, Duration.ofMillis(500))
            .filter(e -> e instanceof WebClientRequestException);

    private final WebClient webClient;

    public AiServerClient(WebClient aiServerWebClient) {
        this.webClient = aiServerWebClient;
    }

    /** 자연어 → 학생 카드 초안 {draft, warnings} */
    /** 문법 질문 답변 (PRD F6-4). 학생을 모르면 nativeLanguage는 ja, studentLevel은 null. */
    public Map<String, Object> grammarQa(String question, String nativeLanguage, Integer studentLevel) {
        Map<String, Object> body = new java.util.HashMap<>();
        body.put("question", question);
        body.put("native_language", nativeLanguage);
        body.put("student_level", studentLevel);
        try {
            return webClient.post().uri("/grammar-qa")
                    .bodyValue(body)
                    .retrieve()
                    .bodyToMono(MAP_TYPE)
                    .retryWhen(CONNECT_RETRY)
                    .block(Duration.ofSeconds(120));
        } catch (WebClientResponseException e) {
            boolean retryable = e.getStatusCode().value() == 502 && e.getResponseBodyAsString().contains("\"retryable\":true");
            throw new AiServerException("AI_SERVER_ERROR", e.getResponseBodyAsString(), retryable, e);
        } catch (RuntimeException e) {
            throw new AiServerException("AI_SERVER_UNAVAILABLE", "ai-server에 연결할 수 없습니다: " + e.getMessage(), true, e);
        }
    }

    public Map<String, Object> intake(String text) {
        try {
            return webClient.post().uri("/intake")
                    .bodyValue(Map.of("text", text))
                    .retrieve()
                    .bodyToMono(MAP_TYPE)
                    .retryWhen(CONNECT_RETRY)
                    .block(Duration.ofSeconds(90));
        } catch (WebClientResponseException e) {
            boolean retryable = e.getStatusCode().value() == 502 && e.getResponseBodyAsString().contains("\"retryable\":true");
            throw new AiServerException("AI_SERVER_ERROR", e.getResponseBodyAsString(), retryable, e);
        } catch (RuntimeException e) {
            throw new AiServerException("AI_SERVER_UNAVAILABLE", "ai-server에 연결할 수 없습니다: " + e.getMessage(), true, e);
        }
    }

    public Flux<ServerSentEvent<String>> prepStart(Map<String, Object> body) {
        return stream("/prep/start", body);
    }

    public Flux<ServerSentEvent<String>> prepResume(String threadId, Map<String, Object> decisions) {
        return stream("/prep/" + threadId + "/resume", Map.of("decisions", decisions));
    }

    public Flux<ServerSentEvent<String>> postLesson(Map<String, Object> body) {
        return stream("/post-lesson", body);
    }

    public Map<String, Object> prepState(String threadId) {
        return webClient.get().uri("/prep/{id}/state", threadId)
                .retrieve().bodyToMono(MAP_TYPE).block(Duration.ofSeconds(10));
    }

    /** 체험수업 레벨테스트 문항 (기획 ADR-0018) */
    public Map<String, Object> levelTest() {
        return call(() -> webClient.get().uri("/level-test")
                .retrieve().bodyToMono(MAP_TYPE).retryWhen(CONNECT_RETRY).block(Duration.ofSeconds(10)));
    }

    /** 레벨테스트 채점 {answers: {문항 ID: bool}} → 추천 등급. 저장하지 않는다. */
    public Map<String, Object> levelTestScore(Map<String, Object> body) {
        return call(() -> webClient.post().uri("/level-test/score").bodyValue(body)
                .retrieve().bodyToMono(MAP_TYPE).retryWhen(CONNECT_RETRY).block(Duration.ofSeconds(10)));
    }

    /** 진도·향상 리포트. 승인 기록·약점을 보내면 숫자와 학생용 문장 초안을 돌려준다 (기획 ADR-0019) */
    public Map<String, Object> progressReport(Map<String, Object> body) {
        return call(() -> webClient.post().uri("/report/progress").bodyValue(body)
                .retrieve().bodyToMono(MAP_TYPE).retryWhen(CONNECT_RETRY).block(Duration.ofSeconds(20)));
    }

    /** 표준 등급 목록 찾아보기. kind = grammar | vocab, 검색 조건은 그대로 넘긴다 */
    public Map<String, Object> standardList(String kind, Map<String, String> params) {
        return call(() -> webClient.get().uri(b -> {
                    b.path("/standard/{kind}");
                    params.forEach((k, v) -> { if (v != null && !v.isBlank()) b.queryParam(k, v); });
                    return b.build(kind);
                })
                .retrieve().bodyToMono(MAP_TYPE).retryWhen(CONNECT_RETRY).block(Duration.ofSeconds(10)));
    }

    /** LangSmith 실행 기록 목록 (기술 ADR-0028). 키는 ai-server에만 있어서 ai-server가 대신 읽는다 */
    public Map<String, Object> traces(Map<String, String> params) {
        return call(() -> webClient.get().uri(b -> {
                    b.path("/traces");
                    params.forEach((k, v) -> { if (v != null && !v.isBlank()) b.queryParam(k, v); });
                    return b.build();
                })
                .retrieve().bodyToMono(MAP_TYPE).retryWhen(CONNECT_RETRY).block(Duration.ofSeconds(30)));
    }

    /** 실행 하나의 트리 (그래프 노드 → 함수 → LLM 호출) */
    public Map<String, Object> trace(java.util.UUID traceId) {
        return call(() -> webClient.get().uri("/traces/{id}", traceId)
                .retrieve().bodyToMono(MAP_TYPE).retryWhen(CONNECT_RETRY).block(Duration.ofSeconds(30)));
    }

    /** 원본 PDF가 등록된 교재 목록 (기술 ADR-0030) */
    public Map<String, Object> materials() {
        return call(() -> webClient.get().uri("/materials")
                .retrieve().bodyToMono(MAP_TYPE).retryWhen(CONNECT_RETRY).block(Duration.ofSeconds(10)));
    }

    /** 교재 원본 PDF를 선생님 컴퓨터에서 그 쪽으로 연다. page = 출처에 적힌 쪽 */
    public Map<String, Object> openMaterial(String book, int page) {
        return call(() -> webClient.post().uri("/materials/open")
                .bodyValue(Map.of("book", book, "page", page))
                .retrieve().bodyToMono(MAP_TYPE).block(Duration.ofSeconds(10)));
    }

    /** 짧은 요청의 에러를 intake와 같은 모양으로 바꾼다. 422(없는 문항 ID)는 다시 해도 같아서 retryable=false */
    private Map<String, Object> call(java.util.function.Supplier<Map<String, Object>> request) {
        try {
            return request.get();
        } catch (WebClientResponseException e) {
            throw new AiServerException("AI_SERVER_ERROR", e.getResponseBodyAsString(), false, e);
        } catch (RuntimeException e) {
            throw new AiServerException("AI_SERVER_UNAVAILABLE", "ai-server에 연결할 수 없습니다: " + e.getMessage(), true, e);
        }
    }

    public byte[] download(String file) {
        return webClient.get().uri(b -> b.path("/files/").path(file).build())
                .retrieve().bodyToMono(byte[].class).block(Duration.ofSeconds(30));
    }

    private Flux<ServerSentEvent<String>> stream(String uri, Object body) {
        return webClient.post().uri(uri)
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(body)
                .retrieve()
                .bodyToFlux(SSE_TYPE)
                .retryWhen(CONNECT_RETRY);
    }
}
