"""FastAPI service. Spring Boot sends it the colleges to compare and the student's request; it sends back a ranking.

Run:  uvicorn main:app --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import chat
from embedder import load_embedder
from scoring import Candidate, Ranker

load_dotenv()  # reads ai-service/.env (GEMINI_API_KEY)
logging.basicConfig(level=logging.INFO)

state: Dict[str, Ranker] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # The model loads once at startup, not on every request
    state["ranker"] = Ranker(load_embedder())
    yield


app = FastAPI(title="College AI ranking service", lifespan=lifespan)


class CandidateIn(BaseModel):
    id: int
    name: str
    city: str
    state: str
    type: Optional[str] = None
    fees_per_year: float
    avg_placement_lpa: Optional[float] = None
    rating: Optional[float] = None
    description: Optional[str] = None


class RankRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    colleges: List[CandidateIn]
    limit: int = Field(default=10, ge=1, le=50)


@app.get("/health")
def health():
    import os

    return {
        "status": "ok",
        "model": state["ranker"].model_name,
        "chat_enabled": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "chat_model": os.getenv("GEMINI_MODEL", "").strip() or chat.DEFAULT_MODEL,
    }


@app.post("/rank")
def rank(request: RankRequest):
    candidates = [Candidate(**c.model_dump()) for c in request.colleges]
    return state["ranker"].rank(request.query, candidates, request.limit)


class ChatMessage(BaseModel):
    role: str
    content: str = Field(max_length=1000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(min_length=1, max_length=20)
    colleges: List[CandidateIn]


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        reply = chat.answer(
            [m.model_dump() for m in request.messages],
            [c.model_dump() for c in request.colleges],
        )
    except chat.ChatError as err:
        return JSONResponse(status_code=err.status, content={"detail": err.message})
    return {"reply": reply}
