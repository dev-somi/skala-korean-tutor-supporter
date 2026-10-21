package com.koreantutor.curriculum;

import com.koreantutor.aiclient.AiServerClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 단원 시트 목록 (기술 ADR-0032). 수업 준비 화면이 교재·과를 고를 때 쓴다.
 * 시트는 ai-server가 가진 파일 데이터라 그대로 넘긴다.
 */
@RestController
@RequestMapping("/api/curriculum")
public class CurriculumController {

    private final AiServerClient aiServer;

    public CurriculumController(AiServerClient aiServer) {
        this.aiServer = aiServer;
    }

    @GetMapping
    public Map<String, Object> list() {
        return aiServer.curriculum();
    }
}
