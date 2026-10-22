package com.koreantutor.chat;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.Map;

/**
 * 대화의 메시지 하나 (기술 ADR-0041). 답은 화면에 보였던 그대로 다시 그릴 수 있게
 * intent·학생·설명 언어·문법 근거·이동 버튼·오류를 meta에 함께 남긴다.
 */
@Entity
@Table(name = "chat_message")
public class ChatMessage {

    public static final String USER = "user";
    public static final String ASSISTANT = "assistant";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String conversationId;
    private String role;
    private String text;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> meta;

    private OffsetDateTime createdAt = OffsetDateTime.now();

    protected ChatMessage() {
    }

    public ChatMessage(String conversationId, String role, String text, Map<String, Object> meta) {
        this.conversationId = conversationId;
        this.role = role;
        this.text = text;
        this.meta = meta;
    }

    public Long getId() { return id; }
    public String getConversationId() { return conversationId; }
    public String getRole() { return role; }
    public String getText() { return text; }
    public Map<String, Object> getMeta() { return meta; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
}
