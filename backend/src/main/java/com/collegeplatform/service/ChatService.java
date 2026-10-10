package com.collegeplatform.service;

import com.collegeplatform.dto.AiDtos.AiCandidate;
import com.collegeplatform.dto.ChatDtos.AiChatRequest;
import com.collegeplatform.dto.ChatDtos.ChatRequest;
import com.collegeplatform.dto.ChatDtos.ChatResponse;
import com.collegeplatform.repository.CollegeRepository;
import java.util.List;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Chatbot: sends the conversation and all colleges to the Python service, where the chat model answers using only that data.
 * The database is read inside a short transaction; the slow HTTP call happens after it is closed.
 */
@Service
public class ChatService {

    private final CollegeRepository colleges;
    private final AiServiceClient ai;
    private final TransactionTemplate tx;

    public ChatService(CollegeRepository colleges, AiServiceClient ai, TransactionTemplate tx) {
        this.colleges = colleges;
        this.ai = ai;
        this.tx = tx;
    }

    public ChatResponse chat(ChatRequest request) {
        List<AiCandidate> all = tx.execute(status -> colleges.findAll(Sort.by("name")).stream()
                .map(c -> new AiCandidate(c.getId(), c.getName(), c.getCity(), c.getState(), c.getType(),
                        c.getFeesPerYear(), c.getAvgPlacementLpa(), c.getRating(), c.getDescription()))
                .toList());
        return new ChatResponse(ai.chat(new AiChatRequest(request.messages(), all)).reply());
    }
}
