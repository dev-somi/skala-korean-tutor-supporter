package com.koreantutor.leveltest;

import com.koreantutor.aiclient.AiServerClient;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * 국립국어원 표준 교육과정 어휘·문법 등급 목록 찾아보기 (기획 ADR-0016).
 * 목록은 ai-server가 가진 파일 데이터라 그대로 넘긴다. 값 검사(등급 1~6 등)는 ai-server가 한다.
 */
@RestController
@RequestMapping("/api/standard")
public class StandardController {

    private final AiServerClient aiServer;

    public StandardController(AiServerClient aiServer) {
        this.aiServer = aiServer;
    }

    @GetMapping("/grammar")
    public Map<String, Object> grammar(@RequestParam(required = false) String level, @RequestParam(required = false) String category,
                                       @RequestParam(required = false) String q) {
        Map<String, String> params = new HashMap<>();
        params.put("level", level);
        params.put("category", category);
        params.put("q", q);
        return aiServer.standardList("grammar", params);
    }

    @GetMapping("/vocab")
    public Map<String, Object> vocab(@RequestParam(required = false) String level, @RequestParam(required = false) String pos,
                                     @RequestParam(required = false) String q, @RequestParam(required = false) String offset,
                                     @RequestParam(required = false) String limit) {
        Map<String, String> params = new HashMap<>();
        params.put("level", level);
        params.put("pos", pos);
        params.put("q", q);
        params.put("offset", offset);
        params.put("limit", limit);
        return aiServer.standardList("vocab", params);
    }
}
