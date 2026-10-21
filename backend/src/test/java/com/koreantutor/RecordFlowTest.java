package com.koreantutor;

import com.koreantutor.aiclient.AiServerClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import reactor.core.publisher.Flux;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** 수업 메모 → AI 초안(미처리) → 항목별 승인 → 약점·수업 이력 반영 */
@Import(TestcontainersConfiguration.class)
@SpringBootTest
@AutoConfigureMockMvc
class RecordFlowTest {

    @Autowired MockMvc mvc;
    @Autowired JsonMapper json;
    @MockitoBean AiServerClient aiServer;

    JsonNode postJson(String url, String body, int status, Object... vars) throws Exception {
        String res = mvc.perform(post(url, vars).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().is(status)).andReturn().getResponse().getContentAsString();
        return json.readTree(res);
    }

    String sse(MvcResult started) throws Exception {
        started.getAsyncResult(10_000);
        return mvc.perform(asyncDispatch(started)).andReturn().getResponse().getContentAsString();
    }

    @Test
    @SuppressWarnings("unchecked")
    void draftThenApproveSelectedItems() throws Exception {
        JsonNode student = postJson("/api/students",
                "{\"name\":\"Emma\",\"nativeLanguage\":\"en\",\"standardLevel\":1,\"weaknesses\":[{\"itemId\":\"u02-g01\",\"description\":\"이/가\"}]}", 201);
        long studentId = student.get("id").asLong();
        long weaknessId = student.get("weaknesses").get(0).get("id").asLong();
        long lessonId = postJson("/api/students/{id}/lessons", "{}", 201, studentId).get("id").asLong();

        String done = """
                {"record_draft":{"covered_item_ids":["u03-v01"],"strengths":["잘함"],"errors":[],
                 "weakness_changes":[{"action":"resolve","weakness_id":%d,"item_id":"u02-g01","description":"이/가"},
                                     {"action":"add","weakness_id":null,"item_id":"u03-g02","description":"을/를"}],
                 "homework":[],"next_lesson_note":"","feedback_message":{"target_lang_text":"Good","korean_text":"좋아요"}},
                 "warnings":["w"],"validation":{"is_acceptable":true,"reasoning":"ok"},"rewrite_count":0}"""
                .formatted(weaknessId).replace("\n", "");
        when(aiServer.postLesson(anyMap())).thenReturn(Flux.just(
                ServerSentEvent.<String>builder().event("started").data("{}").build(),
                ServerSentEvent.<String>builder().event("done").data(done).build()));

        String stream = sse(mvc.perform(post("/api/lessons/{id}/record", lessonId).contentType(MediaType.APPLICATION_JSON)
                .content("{\"rawNote\":\"3과 단어 함\",\"noteStartedAt\":\"2026-10-19T09:00:00+09:00\"}")).andReturn());
        assertThat(stream).contains("event:done");

        // ai-server에 현재 약점(id 포함)을 보냈다
        var captor = org.mockito.ArgumentCaptor.forClass(Map.class);
        verify(aiServer).postLesson(captor.capture());
        assertThat((java.util.List<Map<String, Object>>) captor.getValue().get("current_weaknesses"))
                .extracting(m -> m.get("id")).containsExactly(weaknessId);

        // 승인 전: 미처리 기록으로 보이고, 프로필은 그대로다
        mvc.perform(get("/api/dashboard/todos"))
                .andExpect(jsonPath("$.pendingRecords[?(@.lessonId == %d)]".formatted(lessonId)).exists());
        mvc.perform(get("/api/lessons/{id}/record", lessonId))
                .andExpect(jsonPath("$.draft.warnings[0]").value("w"))
                .andExpect(jsonPath("$.approvedAt").doesNotExist());
        mvc.perform(get("/api/students/{id}", studentId)).andExpect(jsonPath("$.weaknesses.length()").value(1));

        // 다른 학생의 약점은 해결할 수 없다 (권위 게이트 2단계)
        postJson("/api/lessons/{id}/record/approve",
                "{\"coveredItemIds\":[],\"weaknessChanges\":[{\"action\":\"resolve\",\"weaknessId\":999999,\"description\":\"x\"}]}",
                400, lessonId);

        // "을/를 추가"는 체크를 풀고(빼고) 해결만 승인
        String approve = """
                {"coveredItemIds":["u03-v01"],"strengths":["잘함"],
                 "weaknessChanges":[{"action":"resolve","weaknessId":%d,"itemId":"u02-g01","description":"이/가"}],
                 "feedbackMessage":{"target_lang_text":"Good","korean_text":"좋아요"},"nextUnit":4}""".formatted(weaknessId);
        postJson("/api/lessons/{id}/record/approve", approve, 200, lessonId);

        mvc.perform(get("/api/students/{id}", studentId))
                .andExpect(jsonPath("$.weaknesses.length()").value(1))
                .andExpect(jsonPath("$.weaknesses[0].resolved").value(true))
                .andExpect(jsonPath("$.nextUnit").value(4));
        mvc.perform(get("/api/lessons/{id}", lessonId))
                .andExpect(jsonPath("$.status").value("recorded"))
                .andExpect(jsonPath("$.coveredItemIds[0]").value("u03-v01"));
        mvc.perform(get("/api/metrics/time"))
                .andExpect(jsonPath("$.post.sessions").isNumber())
                .andExpect(jsonPath("$.post.recent[?(@.lessonId == %d)]".formatted(lessonId)).exists());

        // 진도 리포트: 승인된 기록과 약점을 ai-server로 보낸다 (기획 ADR-0019)
        when(aiServer.progressReport(anyMap())).thenReturn(Map.of("lessons", Map.of("count", 1)));
        mvc.perform(get("/api/students/{id}/report", studentId).param("from", "2026-01-01"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lessons.count").value(1));
        var reportCaptor = org.mockito.ArgumentCaptor.forClass(Map.class);
        verify(aiServer).progressReport(reportCaptor.capture());
        Map<String, Object> reportBody = reportCaptor.getValue();
        var sentLessons = (java.util.List<Map<String, Object>>) reportBody.get("lessons");
        assertThat(sentLessons).hasSize(1);
        assertThat(sentLessons.get(0).get("covered_item_ids")).isEqualTo(java.util.List.of("u03-v01"));
        assertThat(sentLessons.get(0).get("strengths")).isEqualTo(java.util.List.of("잘함"));
        assertThat(sentLessons.get(0).get("date")).isNotNull(); // 수업 날짜가 없으면 승인한 날
        assertThat((java.util.List<Map<String, Object>>) reportBody.get("weaknesses"))
                .extracting(m -> m.get("resolved")).containsExactly(true);

        // 두 번 승인할 수 없다
        postJson("/api/lessons/{id}/record/approve", approve, 409, lessonId);
    }

    @Test
    void baselineAndReduction() throws Exception {
        mvc.perform(put("/api/baselines/prep").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"minutes\":90,\"note\":\"3과 직접 준비\",\"isEstimate\":true}"))
                .andExpect(status().isOk());
        mvc.perform(get("/api/metrics/time"))
                .andExpect(jsonPath("$.prep.baselineMinutes").value(90))
                .andExpect(jsonPath("$.prep.baselineIsEstimate").value(true));
        mvc.perform(put("/api/baselines/other").contentType(MediaType.APPLICATION_JSON).content("{\"minutes\":5}"))
                .andExpect(status().isBadRequest());
    }
}
