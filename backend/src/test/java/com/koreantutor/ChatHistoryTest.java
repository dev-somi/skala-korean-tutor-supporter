package com.koreantutor;

import com.koreantutor.aiclient.AiServerClient;
import com.koreantutor.chat.RouteDecision;
import com.koreantutor.chat.RouterService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * 채팅 기록 저장 (기술 ADR-0041)과 설명 언어 토글 (기획 ADR-0035).
 * 라우터와 ai-server는 가짜라서 LLM을 부르지 않는 경로(고정 답, 문법 질문)만 쓴다.
 */
@Import(TestcontainersConfiguration.class)
@SpringBootTest
@AutoConfigureMockMvc
class ChatHistoryTest {

    @Autowired MockMvc mvc;

    @MockitoBean RouterService router;
    @MockitoBean AiServerClient aiServer;

    String chat(String message, String conversationId, String lang) throws Exception {
        String body = lang == null
                ? "{\"message\":\"%s\",\"conversationId\":\"%s\"}".formatted(message, conversationId)
                : "{\"message\":\"%s\",\"conversationId\":\"%s\",\"lang\":\"%s\"}".formatted(message, conversationId, lang);
        MvcResult started = mvc.perform(post("/api/chat/stream").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(request().asyncStarted()).andReturn();
        started.getAsyncResult(10_000);
        String sse = mvc.perform(asyncDispatch(started)).andReturn().getResponse().getContentAsString();
        Thread.sleep(200); // 기록은 스트림을 닫은 뒤 finally에서 저장된다
        return sse;
    }

    @Test
    void savesTurnsAndListsRenamesDeletes() throws Exception {
        RouteDecision lookup = new RouteDecision(RouteDecision.LOOKUP, "없는 학생", null, "학생을 찾지 못함");
        when(router.route(anyString(), anyString())).thenReturn(lookup);
        when(router.resolve(any())).thenReturn(new RouterService.Resolved(lookup, null, true));

        chat("없는 학생 요즘 약한 거 뭐야? 아주 길게 써서 제목이 잘리는지 본다", "c-history1", null);
        chat("두 번째 질문", "c-history1", null);

        mvc.perform(get("/api/chat/conversations"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.id == 'c-history1')].title").value("없는 학생 요즘 약한 거 뭐야? 아주 길게 써서 제목이…"));
        mvc.perform(get("/api/chat/conversations/c-history1"))
                .andExpect(jsonPath("$.length()").value(4))
                .andExpect(jsonPath("$[0].role").value("user"))
                .andExpect(jsonPath("$[1].role").value("assistant"))
                .andExpect(jsonPath("$[1].text").value(org.hamcrest.Matchers.containsString("학생을 먼저 등록")))
                .andExpect(jsonPath("$[1].meta.intent").value("lookup"))
                .andExpect(jsonPath("$[1].meta.lang").value("ja"))
                .andExpect(jsonPath("$[3].role").value("assistant"));

        mvc.perform(patch("/api/chat/conversations/c-history1").contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"새 제목\"}"))
                .andExpect(jsonPath("$.title").value("새 제목"));
        mvc.perform(delete("/api/chat/conversations/c-history1")).andExpect(status().isNoContent());
        mvc.perform(get("/api/chat/conversations/c-history1")).andExpect(status().isNotFound());
    }

    @Test
    void grammarAnswerKeepsSourcesAndUsesToggledLanguage() throws Exception {
        RouteDecision grammar = new RouteDecision(RouteDecision.GRAMMAR_QA, null, null, "문법 비교");
        when(router.route(anyString(), anyString())).thenReturn(grammar);
        when(router.resolve(any())).thenReturn(new RouterService.Resolved(grammar, null, false));
        when(aiServer.grammarQa(anyString(), eq("en"), isNull())).thenReturn(Map.of(
                "points", List.of("이유를 말할 때 -아서", "명령·청유에는 -(으)니까"),
                "forms", List.of(Map.of("form", "-아서")),
                "out_of_level", List.of(), "ungrounded_forms", List.of(), "removed_points", List.of(), "ai_note", ""));

        String sse = chat("-아서랑 -(으)니까 차이", "c-history2", "en");
        assertThat(sse).contains("\"lang\":\"en\"").contains("event:sources");
        verify(aiServer).grammarQa(anyString(), eq("en"), isNull());

        mvc.perform(get("/api/chat/conversations/c-history2"))
                .andExpect(jsonPath("$[1].text").value("• 이유를 말할 때 -아서\n• 명령·청유에는 -(으)니까"))
                .andExpect(jsonPath("$[1].meta.lang").value("en"))
                .andExpect(jsonPath("$[1].meta.sources.forms[0].form").value("-아서"));
    }

    @Test
    void rejectsUnknownLanguage() throws Exception {
        mvc.perform(post("/api/chat/stream").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"message\":\"안녕\",\"conversationId\":\"c-x\",\"lang\":\"zh\"}"))
                .andExpect(status().isBadRequest());
    }
}
