package com.koreantutor.lesson;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.aiclient.SseRelay;
import com.koreantutor.lesson.LessonDtos.CategoryDecision;
import com.koreantutor.timelog.TimeLog;
import com.koreantutor.timelog.TimeLogService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 수업 준비(lesson_prep) 흐름: ai-server 그래프를 실행하고 진행 상황을 브라우저로 중계한다.
 * done 이벤트를 받으면 결과를 저장하고 수업 준비 시간 측정을 끝낸다 (PRD F7-1).
 */
@Service
public class PrepService {

    private static final Logger log = LoggerFactory.getLogger(PrepService.class);
    private static final TypeReference<Map<String, Object>> MAP = new TypeReference<>() {
    };

    private final LessonService lessons;
    private final AiServerClient aiServer;
    private final SseRelay relay;
    private final TimeLogService timeLogs;
    private final JsonMapper json;
    private final ReviewDecisionRepository decisionLog;

    public PrepService(LessonService lessons, AiServerClient aiServer, SseRelay relay,
                       TimeLogService timeLogs, JsonMapper json, ReviewDecisionRepository decisionLog) {
        this.lessons = lessons;
        this.aiServer = aiServer;
        this.relay = relay;
        this.timeLogs = timeLogs;
        this.json = json;
        this.decisionLog = decisionLog;
    }

    public SseEmitter start(Long lessonId) {
        Map<String, Object> body = lessons.beginPrep(lessonId);
        log.info("prep start lesson_id={} thread_id={}", lessonId, body.get("thread_id"));
        return relayFor(lessonId, aiServer.prepStart(body));
    }

    public SseEmitter review(Long lessonId, Map<String, CategoryDecision> decisions) {
        String threadId = lessons.reviewableThread(lessonId);
        // 품질 지표용: 범주별 결정을 남긴다 (기획 ADR-0020)
        decisionLog.saveAll(decisions.entrySet().stream()
                .map(e -> new ReviewDecision(lessonId, e.getKey(), e.getValue().action())).toList());
        Map<String, Object> body = new LinkedHashMap<>();
        decisions.forEach((category, d) -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("action", d.action());
            // 보내지 않은 칸은 빼서, ai-server가 기존 초안을 유지하게 한다
            if (d.explanation() != null) m.put("explanation", d.explanation());
            if (d.script() != null) m.put("script", d.script());
            if (d.feedback() != null) m.put("feedback", d.feedback());
            body.put(category, m);
        });
        return relayFor(lessonId, aiServer.prepResume(threadId, body));
    }

    public Map<String, Object> state(Long lessonId) {
        return aiServer.prepState(lessons.threadOf(lessonId));
    }

    private SseEmitter relayFor(Long lessonId, reactor.core.publisher.Flux<ServerSentEvent<String>> source) {
        return relay.relay(source,
                (event, elapsed) -> onEvent(lessonId, event, elapsed),
                elapsed -> timeLogs.addAiWait(lessonId, TimeLog.PREP, elapsed));
    }

    private void onEvent(Long lessonId, ServerSentEvent<String> event, Duration elapsed) {
        if ("done".equals(event.event())) {
            lessons.completePrep(lessonId, json.readValue(event.data(), MAP));
            // 마지막 스트림의 AI 대기 시간을 먼저 더한 뒤 끝낸다 (끝난 뒤에는 더할 곳이 없다)
            timeLogs.addAiWait(lessonId, TimeLog.PREP, elapsed);
            timeLogs.finish(lessonId, TimeLog.PREP);
            log.info("prep done lesson_id={}", lessonId);
        }
    }
}
