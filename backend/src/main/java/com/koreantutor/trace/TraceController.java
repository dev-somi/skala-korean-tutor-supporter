package com.koreantutor.trace;

import com.koreantutor.aiclient.AiServerClient;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * AI 추적 화면 (기술 ADR-0028). LangSmith에 쌓인 ai-server 실행 기록을 ai-server를 거쳐 그대로 돌려준다.
 * 저장하지 않는다. Spring AI 채팅 호출은 아직 추적하지 않는다.
 */
@RestController
@RequestMapping("/api/traces")
public class TraceController {

    private final AiServerClient aiServer;

    public TraceController(AiServerClient aiServer) {
        this.aiServer = aiServer;
    }

    /** name: lesson_prep | post_lesson | student_intake | grammar_qa (없으면 전체) */
    @GetMapping
    public Map<String, Object> list(@RequestParam(required = false) Integer limit,
                                    @RequestParam(required = false) String name,
                                    @RequestParam(required = false) Boolean errorsOnly) {
        Map<String, String> params = new HashMap<>();
        if (limit != null) params.put("limit", limit.toString());
        params.put("name", name);
        if (errorsOnly != null) params.put("errors_only", errorsOnly.toString());
        return aiServer.traces(params);
    }

    @GetMapping("/{traceId}")
    public Map<String, Object> get(@PathVariable UUID traceId) {
        return aiServer.trace(traceId);
    }
}
