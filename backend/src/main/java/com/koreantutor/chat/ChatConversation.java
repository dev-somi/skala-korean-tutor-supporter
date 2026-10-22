package com.koreantutor.chat;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;

/** 채팅 대화 하나 (기술 ADR-0041). id는 프론트가 만든 conversationId다. */
@Entity
@Table(name = "chat_conversation")
public class ChatConversation {

    public static final int TITLE_LENGTH = 30;

    @Id
    private String id;

    private String title;
    private OffsetDateTime createdAt = OffsetDateTime.now();
    private OffsetDateTime updatedAt = OffsetDateTime.now();

    protected ChatConversation() {
    }

    /** 제목은 첫 질문 앞부분으로 정한다 (LLM 호출 없음) */
    public ChatConversation(String id, String firstMessage) {
        this.id = id;
        String oneLine = firstMessage.strip().replaceAll("\\s+", " ");
        this.title = oneLine.length() > TITLE_LENGTH ? oneLine.substring(0, TITLE_LENGTH) + "…" : oneLine;
    }

    public void rename(String title) {
        this.title = title;
    }

    public void touch() {
        this.updatedAt = OffsetDateTime.now();
    }

    public String getId() { return id; }
    public String getTitle() { return title; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
}
