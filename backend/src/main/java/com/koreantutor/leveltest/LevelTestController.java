package com.koreantutor.leveltest;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.leveltest.LevelTestResultService.ResultView;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 체험수업 레벨테스트 (기획 ADR-0018, ADR-0021, 기술 ADR-0017, ADR-0019).
 * 문항과 채점 규칙은 표준 등급 목록을 가진 ai-server에 있고, 여기서는 그대로 넘긴다.
 * [결과 저장]하면 판정 결과를 남긴다. 학생 카드에는 선생님이 확인(apply)해야 들어간다.
 */
@RestController
@RequestMapping("/api/level-test")
public class LevelTestController {

    private final AiServerClient aiServer;
    private final LevelTestResultService results;

    public LevelTestController(AiServerClient aiServer, LevelTestResultService results) {
        this.aiServer = aiServer;
        this.results = results;
    }

    public record ScoreRequest(@NotNull Map<String, Boolean> answers) {
    }

    public record SaveRequest(@NotNull Map<String, Boolean> answers, String note) {
    }

    /** level이 없으면 추천 등급으로 반영한다 */
    public record ApplyRequest(@NotNull Long studentId, @Min(0) @Max(6) Integer level) {
    }

    @GetMapping
    public Map<String, Object> get() {
        return aiServer.levelTest();
    }

    @PostMapping("/score")
    public Map<String, Object> score(@Valid @RequestBody ScoreRequest req) {
        return aiServer.levelTestScore(Map.of("answers", req.answers()));
    }

    @PostMapping("/results")
    @ResponseStatus(HttpStatus.CREATED)
    public ResultView save(@Valid @RequestBody SaveRequest req) {
        return results.save(req.answers(), req.note());
    }

    @GetMapping("/results")
    public List<ResultView> pending() {
        return results.pending();
    }

    @GetMapping("/results/{id}")
    public ResultView result(@PathVariable Long id) {
        return results.get(id);
    }

    @PostMapping("/results/{id}/apply")
    public ResultView apply(@PathVariable Long id, @Valid @RequestBody ApplyRequest req) {
        return results.apply(id, req.studentId(), req.level());
    }

    @PostMapping("/results/{id}/dismiss")
    public ResultView dismiss(@PathVariable Long id) {
        return results.dismiss(id);
    }
}
