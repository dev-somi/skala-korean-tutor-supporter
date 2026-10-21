package com.koreantutor.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
@EnableConfigurationProperties(AppProperties.class)
public class WebClientConfig {

    @Bean
    WebClient aiServerWebClient(WebClient.Builder builder, AppProperties props) {
        return builder
                .baseUrl(props.aiServer().url())
                // PPT 파일을 내려받을 때를 위해 버퍼를 넉넉히 (기본 256KB)
                .codecs(c -> c.defaultCodecs().maxInMemorySize(32 * 1024 * 1024))
                .build();
    }
}
