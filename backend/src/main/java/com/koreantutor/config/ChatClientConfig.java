package com.koreantutor.config;

import org.springframework.ai.anthropic.AnthropicChatOptions;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.ai.chat.memory.MessageWindowChatMemory;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.prompt.ChatOptions;
import org.springframework.ai.ollama.OllamaChatModel;
import org.springframework.ai.ollama.api.OllamaChatOptions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 모델 티어링 (ADR-0007): 라우팅·조회 답변은 fast(Haiku), 한국어 교육 질문 답변은 quality(Sonnet).
 * 모델 이름은 .env의 LLM_MODEL_FAST / LLM_MODEL_QUALITY.
 * 어떤 ChatModel이 들어올지는 .env의 LLM_PROVIDER(anthropic | ollama)가 정한다 (ADR-0012).
 */
@Configuration
public class ChatClientConfig {

    @Value("${app.ollama.num-ctx:16384}")
    private int ollamaNumCtx;

    @Bean
    ChatClient fastChatClient(ChatModel chatModel, AppProperties props) {
        return ChatClient.builder(chatModel)
                .defaultOptions(options(chatModel, props.models().fastModel(), 2048))
                .build();
    }

    @Bean
    ChatClient qualityChatClient(ChatModel chatModel, AppProperties props) {
        return ChatClient.builder(chatModel)
                .defaultOptions(options(chatModel, props.models().qualityModel(), 4096))
                .build();
    }

    /** 로컬 Ollama는 기본 컨텍스트(4096)를 늘리고, qwen3의 생각(thinking) 출력을 끈다 */
    private ChatOptions.Builder<?> options(ChatModel chatModel, String model, int maxTokens) {
        if (chatModel instanceof OllamaChatModel) {
            return OllamaChatOptions.builder().model(model).numPredict(maxTokens).numCtx(ollamaNumCtx).disableThinking();
        }
        return AnthropicChatOptions.builder().model(model).maxTokens(maxTokens);
    }

    /** 채팅 대화 기록 (MVP: 메모리, 최근 20개 메시지) */
    @Bean
    ChatMemory chatMemory() {
        return MessageWindowChatMemory.builder().maxMessages(20).build();
    }
}
