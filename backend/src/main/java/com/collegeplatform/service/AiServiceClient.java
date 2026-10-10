package com.collegeplatform.service;

import com.collegeplatform.dto.AiDtos.AiRankRequest;
import com.collegeplatform.dto.AiDtos.AiRankResponse;
import com.collegeplatform.dto.ChatDtos.AiChatRequest;
import com.collegeplatform.dto.ChatDtos.AiChatResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.ClientHttpRequestFactories;
import org.springframework.boot.web.client.ClientHttpRequestFactorySettings;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.server.ResponseStatusException;

/** Thin HTTP client for the Python ranking service. */
@Component
public class AiServiceClient {

    private final RestClient http;

    public AiServiceClient(@Value("${app.ai.url}") String baseUrl) {
        ClientHttpRequestFactorySettings settings = ClientHttpRequestFactorySettings.DEFAULTS
                .withConnectTimeout(Duration.ofSeconds(3))
                .withReadTimeout(Duration.ofSeconds(30));
        this.http = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(ClientHttpRequestFactories.get(settings))
                .build();
    }

    public AiRankResponse rank(AiRankRequest request) {
        try {
            AiRankResponse response = http.post().uri("/rank").body(request).retrieve().body(AiRankResponse.class);
            if (response == null) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI service returned an empty response");
            }
            return response;
        } catch (RestClientException e) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "The AI service is not reachable. Start it with: uvicorn main:app --port 8000",
                    e);
        }
    }

    /** Chatbot call. The Python service sends back {"detail": "..."} on errors; pass that message on to the browser. */
    public AiChatResponse chat(AiChatRequest request) {
        try {
            AiChatResponse response = http.post().uri("/chat").body(request).retrieve().body(AiChatResponse.class);
            if (response == null || response.reply() == null) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI service returned an empty reply");
            }
            return response;
        } catch (RestClientResponseException e) {
            throw new ResponseStatusException(HttpStatus.valueOf(e.getStatusCode().value()), detailOf(e), e);
        } catch (RestClientException e) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "The AI service is not reachable. Start it with: uvicorn main:app --port 8000",
                    e);
        }
    }

    private static String detailOf(RestClientResponseException e) {
        try {
            JsonNode detail = new ObjectMapper().readTree(e.getResponseBodyAsString()).get("detail");
            if (detail != null && detail.isTextual()) {
                return detail.asText();
            }
        } catch (Exception ignored) {
            // fall through to the generic message
        }
        return "The chat service returned an error";
    }
}
