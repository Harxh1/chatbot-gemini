package com.collegeplatform.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.List;

/** Request/response shapes for the chatbot. */
public final class ChatDtos {

    private ChatDtos() {
    }

    public record ChatMessage(
            @Pattern(regexp = "user|assistant", message = "role must be user or assistant") String role,
            @NotBlank @Size(max = 1000, message = "Keep each message under 1000 characters") String content) {
    }

    /** What the browser sends: the conversation so far, oldest first, ending with the student's new message. */
    public record ChatRequest(
            @NotEmpty @Size(max = 20, message = "Conversation is too long") List<@Valid ChatMessage> messages) {
    }

    /** What goes to the Python service: the conversation plus every college, so the bot can only use real data. */
    public record AiChatRequest(List<ChatMessage> messages, List<AiDtos.AiCandidate> colleges) {
    }

    public record AiChatResponse(String reply) {
    }

    public record ChatResponse(String reply) {
    }
}
