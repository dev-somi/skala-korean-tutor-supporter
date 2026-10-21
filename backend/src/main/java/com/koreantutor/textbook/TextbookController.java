package com.koreantutor.textbook;

import com.koreantutor.aiclient.AiServerClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 교재 항목 ID(u03-v01)를 화면에 보일 이름("노래")으로 바꾸는 목록 (기술 ADR-0029).
 * 교재 데이터는 ai-server가 가진 파일이라 그대로 넘긴다.
 */
@RestController
@RequestMapping("/api/textbook")
public class TextbookController {

    private final AiServerClient aiServer;

    public TextbookController(AiServerClient aiServer) {
        this.aiServer = aiServer;
    }

    @GetMapping("/items")
    public Map<String, Object> items() {
        return aiServer.textbookItems();
    }
}
