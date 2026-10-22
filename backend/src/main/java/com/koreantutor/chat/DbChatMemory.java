package com.koreantutor.chat;

import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.data.domain.PageRequest;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * chat_message 표를 읽는 ChatMemory (기술 ADR-0041). 화면 기록과 LLM 문맥이 같은 데이터를 본다.
 * 쓰기는 ChatService가 meta와 함께 한 번에 하므로 add()는 아무것도 하지 않는다
 * (MessageChatMemoryAdvisor가 부르는 add()로 두 번 저장되지 않게).
 */
public class DbChatMemory implements ChatMemory {

    private final ChatMessageRepository messages;
    private final int maxMessages;

    public DbChatMemory(ChatMessageRepository messages, int maxMessages) {
        this.messages = messages;
        this.maxMessages = maxMessages;
    }

    @Override
    public void add(String conversationId, List<Message> newMessages) {
    }

    @Override
    public List<Message> get(String conversationId) {
        List<Message> out = new ArrayList<>();
        for (ChatMessage m : messages.findByConversationIdOrderByIdDesc(conversationId, PageRequest.of(0, maxMessages))) {
            if (m.getText().isBlank()) continue;
            out.add(ChatMessage.USER.equals(m.getRole()) ? new UserMessage(m.getText()) : new AssistantMessage(m.getText()));
        }
        Collections.reverse(out);
        return out;
    }

    @Override
    public void clear(String conversationId) {
    }
}
