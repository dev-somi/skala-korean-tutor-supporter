package com.koreantutor.timelog;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class MetricsController {

    private final MetricsService service;

    public MetricsController(MetricsService service) {
        this.service = service;
    }

    public record BaselineRequest(@Min(1) @Max(600) int minutes, String note, Boolean isEstimate) {
    }

    @GetMapping("/metrics/time")
    public Map<String, MetricsService.KindSummary> time() {
        return service.summary();
    }

    /** 주 지표: AI 초안을 그대로 승인한 비율 (기획 ADR-0020) */
    @GetMapping("/metrics/quality")
    public Map<String, Map<String, QualityMetrics.Rate>> quality() {
        return service.quality();
    }

    @PutMapping("/baselines/{kind}")
    public Map<String, Object> saveBaseline(@PathVariable String kind, @Valid @RequestBody BaselineRequest req) {
        Baseline b = service.saveBaseline(kind, req.minutes(), req.note(), Boolean.TRUE.equals(req.isEstimate()));
        return Map.of("kind", b.getKind(), "minutes", b.getMinutes(), "note", b.getNote(), "isEstimate", b.isEstimate());
    }
}
