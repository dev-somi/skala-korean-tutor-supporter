package com.koreantutor;

import com.koreantutor.aiclient.AiServerClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import reactor.core.publisher.Flux;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * 학생 등록 → 수업 생성 → 수업 준비(SSE) → 검토 → 결과 저장·시간 기록까지.
 * ai-server는 가짜(AiServerClient mock), DB는 Testcontainers Postgres.
 */
@Import(TestcontainersConfiguration.class)
@SpringBootTest
@AutoConfigureMockMvc
class StudentAndPrepFlowTest {

    @Autowired MockMvc mvc;
    @Autowired JsonMapper json;
    @Autowired JdbcTemplate jdbc;

    @MockitoBean AiServerClient aiServer;

    static ServerSentEvent<String> event(String name, String data) {
        return ServerSentEvent.<String>builder().event(name).data(data).build();
    }

    long createStudent() throws Exception {
        String body = """
                {"name":"사토 유이","nativeLanguage":"ja","nextUnit":3,"standardLevel":1,"persona":"travel",
                 "weaknesses":[{"itemId":"u02-g01","description":"이/가"},{"description":"받침 발음"}]}""";
        String res = mvc.perform(post("/api/students").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(res).get("id").asLong();
    }

    long createLesson(long studentId) throws Exception {
        String res = mvc.perform(post("/api/students/{id}/lessons", studentId).contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.unitNo").value(3))
                .andExpect(jsonPath("$.minutes").value(50))
                .andExpect(jsonPath("$.targetLang").value("ja"))
                .andReturn().getResponse().getContentAsString();
        return json.readTree(res).get("id").asLong();
    }

    String sse(MvcResult started) throws Exception {
        started.getAsyncResult(10_000);
        return mvc.perform(asyncDispatch(started)).andReturn().getResponse().getContentAsString();
    }

    @Test
    void validationErrorsHaveCodeAndMessage() throws Exception {
        mvc.perform(post("/api/students").contentType(MediaType.APPLICATION_JSON).content("{\"name\":\"\",\"nativeLanguage\":\"zh\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
        mvc.perform(post("/api/students").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"a\",\"nativeLanguage\":\"ja\",\"standardLevel\":1,\"weaknesses\":[{\"itemId\":\"bad\",\"description\":\"x\"}]}"))
                .andExpect(status().isBadRequest());
        // 현재 수준(표준 등급)은 필수다 (기획 ADR-0018). 범위 밖 등급, 모르는 학습 목적도 막는다
        for (String body : java.util.List.of(
                "{\"name\":\"a\",\"nativeLanguage\":\"ja\"}",
                "{\"name\":\"a\",\"nativeLanguage\":\"ja\",\"standardLevel\":7}",
                "{\"name\":\"a\",\"nativeLanguage\":\"ja\",\"standardLevel\":1,\"persona\":\"kpop\"}")) {
            mvc.perform(post("/api/students").contentType(MediaType.APPLICATION_JSON).content(body))
                    .andExpect(status().isBadRequest());
        }
    }

    @Test
    void updateSyncsWeaknesses() throws Exception {
        long id = createStudent();
        String res = mvc.perform(get("/api/students/{id}", id)).andReturn().getResponse().getContentAsString();
        long firstWeakness = json.readTree(res).get("weaknesses").get(0).get("id").asLong();

        // 첫 약점은 해결, 둘째는 목록에서 빠짐(삭제), 새 약점 추가
        String update = """
                {"name":"사토 유이","nativeLanguage":"ja","standardLevel":1,
                 "weaknesses":[{"id":%d,"itemId":"u02-g01","description":"이/가","resolved":true},{"description":"을/를"}]}"""
                .formatted(firstWeakness);
        mvc.perform(put("/api/students/{id}", id).contentType(MediaType.APPLICATION_JSON).content(update))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.weaknesses.length()").value(2))
                .andExpect(jsonPath("$.weaknesses[0].resolved").value(true))
                .andExpect(jsonPath("$.weaknesses[1].id").isNumber());

        mvc.perform(get("/api/students"))
                .andExpect(jsonPath("$[?(@.id == %d)].mainWeaknesses[0]".formatted(id)).value("을/를"));
    }

    @Test
    void lessonsInRangeForCalendar() throws Exception {
        long studentId = createStudent();
        long inRange = createLessonOn(studentId, "\"2031-05-10\"");
        long outOfRange = createLessonOn(studentId, "\"2031-06-02\"");
        long undated = createLessonOn(studentId, "null");

        mvc.perform(get("/api/lessons").param("from", "2031-05-01").param("to", "2031-05-31"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.id == %d)].studentName".formatted(inRange)).value("사토 유이"))
                .andExpect(jsonPath("$[?(@.id == %d)]".formatted(outOfRange)).doesNotExist())
                .andExpect(jsonPath("$[?(@.id == %d)]".formatted(undated)).exists());
    }

    long createLessonOn(long studentId, String lessonDateJson) throws Exception {
        String res = mvc.perform(post("/api/students/{id}/lessons", studentId).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"lessonDate\":" + lessonDateJson + "}"))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(res).get("id").asLong();
    }

    @Test
    @SuppressWarnings("unchecked")
    void prepFlowSavesResultAndTimeLog() throws Exception {
        long studentId = createStudent();
        long lessonId = createLesson(studentId);

        when(aiServer.prepStart(anyMap())).thenReturn(Flux.just(
                event("started", "{\"thread_id\":\"t\"}"),
                event("node_finished", "{\"node\":\"plan_lesson\"}"),
                event("review_required", "{\"drafts\":{}}")));

        String first = sse(mvc.perform(post("/api/lessons/{id}/prep", lessonId)).andExpect(request().asyncStarted()).andReturn());
        assertThat(first).contains("event:started", "event:node_finished", "event:review_required");

        // Spring이 DB에서 조립해 보낸 프로필 확인 (ADR-0005)
        var captor = org.mockito.ArgumentCaptor.forClass(Map.class);
        verify(aiServer).prepStart(captor.capture());
        Map<String, Object> body = captor.getValue();
        Map<String, Object> profile = (Map<String, Object>) body.get("profile");
        assertThat(profile.get("weaknesses")).isEqualTo(java.util.List.of("u02-g01"));
        assertThat(profile.get("weakness_notes")).isEqualTo(java.util.List.of("받침 발음"));
        assertThat(profile.get("standard_level")).isEqualTo(1);
        assertThat(profile.get("persona")).isEqualTo("travel");
        assertThat(body.get("output_subdir")).isEqualTo("stu-" + studentId + "/lesson-" + lessonId);
        String threadId = (String) body.get("thread_id");

        mvc.perform(get("/api/dashboard/todos")).andExpect(jsonPath("$.pendingPrep[?(@.id == %d)]".formatted(lessonId)).exists());

        String done = """
                {"thread_id":"%s","pptx_file":"stu-1/lesson-1/a.pptx","pdf_file":null,
                 "plan":{"review":{"item_ids":[],"minutes":10,"reason":"r"}},"briefing":{"tips":["t"]},"drafts":{}}"""
                .formatted(threadId).replace("\n", "");
        when(aiServer.prepResume(anyString(), anyMap())).thenReturn(Flux.just(event("done", done)));

        String review = "{\"decisions\":{\"review\":{\"action\":\"approve\"}}}";
        String second = sse(mvc.perform(post("/api/lessons/{id}/prep/review", lessonId)
                .contentType(MediaType.APPLICATION_JSON).content(review)).andReturn());
        assertThat(second).contains("event:done");

        mvc.perform(get("/api/lessons/{id}", lessonId))
                .andExpect(jsonPath("$.status").value("prepared"))
                .andExpect(jsonPath("$.pptxFile").value("stu-1/lesson-1/a.pptx"))
                .andExpect(jsonPath("$.plan.review.minutes").value(10))
                .andExpect(jsonPath("$.briefing.tips[0]").value("t"));

        Integer open = jdbc.queryForObject(
                "select count(*) from time_log where lesson_id = ? and kind = 'prep' and finished_at is null", Integer.class, lessonId);
        Integer closed = jdbc.queryForObject(
                "select count(*) from time_log where lesson_id = ? and kind = 'prep' and teacher_seconds is not null", Integer.class, lessonId);
        assertThat(open).isZero();
        assertThat(closed).isEqualTo(1);

        // 확정된 뒤에는 검토를 다시 보낼 수 없다
        mvc.perform(post("/api/lessons/{id}/prep/review", lessonId).contentType(MediaType.APPLICATION_JSON).content(review))
                .andExpect(status().isConflict());
    }

    @Test
    void aiServerStreamErrorBecomesErrorEvent() throws Exception {
        long lessonId = createLesson(createStudent());
        when(aiServer.prepStart(any())).thenReturn(Flux.error(new IllegalStateException("boom")));
        String body = sse(mvc.perform(post("/api/lessons/{id}/prep", lessonId)).andReturn());
        assertThat(body).contains("event:error", "AI_SERVER_ERROR");
    }
}
