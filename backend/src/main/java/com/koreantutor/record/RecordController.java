package com.koreantutor.record;

import com.koreantutor.record.RecordDtos.*;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/lessons/{lessonId}/record")
public class RecordController {

    private final RecordService service;

    public RecordController(RecordService service) {
        this.service = service;
    }

    /** 수업 메모 → AI 초안 (SSE). 이벤트: started, node_finished, done, error */
    @PostMapping(produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter draft(@PathVariable Long lessonId, @Valid @RequestBody RecordRequest req) {
        return service.draft(lessonId, req);
    }

    @GetMapping
    public RecordView get(@PathVariable Long lessonId) {
        return service.get(lessonId);
    }

    /** 선생님이 승인한 항목만 반영 */
    @PostMapping("/approve")
    public RecordView approve(@PathVariable Long lessonId, @Valid @RequestBody ApproveRequest req) {
        return service.approve(lessonId, req);
    }
}
