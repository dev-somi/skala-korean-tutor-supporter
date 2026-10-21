package com.koreantutor.material;

import com.koreantutor.aiclient.AiServerClient;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 출처로 찾은 교재 원본 PDF 열기 (기술 ADR-0030).
 * 파일은 네트워크로 보내지 않는다. 로컬에서 도는 ai-server가 선생님 컴퓨터의 PDF를 그 쪽으로 연다.
 */
@RestController
@RequestMapping("/api/materials")
public class MaterialController {

    private final AiServerClient aiServer;

    public MaterialController(AiServerClient aiServer) {
        this.aiServer = aiServer;
    }

    public record OpenRequest(@NotBlank String book, @Min(1) int page) {
    }

    @GetMapping
    public Map<String, Object> list() {
        return aiServer.materials();
    }

    @PostMapping("/open")
    public Map<String, Object> open(@Valid @RequestBody OpenRequest body) {
        return aiServer.openMaterial(body.book(), body.page());
    }
}
