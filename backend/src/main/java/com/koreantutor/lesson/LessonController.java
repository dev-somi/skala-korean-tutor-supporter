package com.koreantutor.lesson;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.lesson.LessonDtos.*;
import jakarta.validation.Valid;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class LessonController {

    private final LessonService lessons;
    private final PrepService prep;
    private final AiServerClient aiServer;

    public LessonController(LessonService lessons, PrepService prep, AiServerClient aiServer) {
        this.lessons = lessons;
        this.prep = prep;
        this.aiServer = aiServer;
    }

    @PostMapping("/students/{studentId}/lessons")
    @ResponseStatus(HttpStatus.CREATED)
    public LessonView create(@PathVariable Long studentId, @Valid @RequestBody CreateLessonRequest req) {
        return lessons.create(studentId, req);
    }

    @GetMapping("/students/{studentId}/lessons")
    public List<LessonView> list(@PathVariable Long studentId) {
        return lessons.listByStudent(studentId);
    }

    /** 대시보드 달력: from~to 사이 수업 + 날짜 미정 수업 (기술 ADR-0039) */
    @GetMapping("/lessons")
    public List<LessonView> listInRange(@RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                        @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        return lessons.listInRange(from, to);
    }

    @GetMapping("/lessons/{id}")
    public LessonView get(@PathVariable Long id) {
        return lessons.get(id);
    }

    /** 수업 준비 시작 (SSE). 이벤트: started, node_finished, review_required, error */
    @PostMapping(value = "/lessons/{id}/prep", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter startPrep(@PathVariable Long id) {
        return prep.start(id);
    }

    /** 범주별 검토 결과 보내기 (SSE). 이벤트: …, review_required(남은 범주) 또는 done */
    @PostMapping(value = "/lessons/{id}/prep/review", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter review(@PathVariable Long id, @Valid @RequestBody PrepReviewRequest req) {
        return prep.review(id, req.decisions());
    }

    /** 지금 검토 화면에 보여 줄 내용 (새로고침 대비) */
    @GetMapping("/lessons/{id}/prep/state")
    public Map<String, Object> prepState(@PathVariable Long id) {
        return prep.state(id);
    }

    /** 만든 자료 내려받기. kind = pptx | pdf */
    @GetMapping("/lessons/{id}/files/{kind}")
    public ResponseEntity<byte[]> download(@PathVariable Long id, @PathVariable String kind) {
        String file = lessons.fileOf(id, kind);
        String name = file.substring(file.lastIndexOf('/') + 1);
        MediaType type = "pdf".equals(kind) ? MediaType.APPLICATION_PDF
                : MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.presentationml.presentation");
        return ResponseEntity.ok()
                .contentType(type)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment().filename(name, StandardCharsets.UTF_8).build().toString())
                .body(aiServer.download(file));
    }
}
