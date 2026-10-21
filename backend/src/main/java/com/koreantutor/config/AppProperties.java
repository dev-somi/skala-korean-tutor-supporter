package com.koreantutor.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

@ConfigurationProperties(prefix = "app")
public record AppProperties(AiServer aiServer, Models models) {

    public record AiServer(String url, Duration sseTimeout) {
    }

    /** .env의 LLM_MODEL_FAST / LLM_MODEL_QUALITY. ai-server용 "anthropic:" 접두어가 붙어 있으면 뗀다. */
    public record Models(String fast, String quality) {
        public String fastModel() { return strip(fast); }
        public String qualityModel() { return strip(quality); }

        private static String strip(String value) {
            int i = value.indexOf(':');
            return i >= 0 ? value.substring(i + 1) : value;
        }
    }
}
