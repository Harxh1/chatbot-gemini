# College Search Platform (MVP)

Backend (Spring Boot + MySQL) is ready. Frontend (React) and the AI ranking service come next.

```
college-platform/
├── database/   schema.sql, seed.sql
└── backend/    Spring Boot 3, Java 17, Maven
```

## Run it

1. **Database**
   ```bash
   mysql -u root -p < database/schema.sql
   mysql -u root -p college_db < database/seed.sql
   ```
2. **Backend** (defaults: user `root`, password `root`; override with env vars)
   ```bash
   cd backend
   export DB_USER=root DB_PASSWORD=your_password   # Windows: set DB_USER=... / set DB_PASSWORD=...
   mvn spring-boot:run
   ```
   API runs at http://localhost:8080

Seed data is illustrative (42 colleges, 8 courses). Fees and placement numbers are approximations, not official figures.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/colleges` | Listing, search and filters (paginated) |
| GET | `/api/colleges/{id}` | One college |
| GET | `/api/meta/states` | State names for the filter dropdown |
| GET | `/api/meta/courses` | Course names for the filter dropdown |
| POST | `/api/recommendations` | Priority-based search (top 10) |

### `GET /api/colleges` parameters (all optional)

`q` (name contains), `state`, `city`, `course`, `minFees`, `maxFees`, `page` (default 0), `size` (default 12, max 50), `sortBy` (`name` | `feesPerYear` | `avgPlacementLpa` | `rating`), `direction` (`asc` | `desc`).

```bash
curl "http://localhost:8080/api/colleges?page=0&size=5"
curl "http://localhost:8080/api/colleges?state=Tamil%20Nadu&course=B.Tech&maxFees=200000"
curl "http://localhost:8080/api/colleges?q=iit&sortBy=rating&direction=desc"
```

### `POST /api/recommendations`

`priorities`: 1 or 2 of `low_fees`, `high_placements`, `top_rated` (most important first). `state` and `course` are optional pre-filters.

```bash
curl -X POST http://localhost:8080/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"priorities":["low_fees","high_placements"],"state":"Tamil Nadu","course":"B.Tech"}'
```

Each result has the college, a `score` (0-100) and `reasons` explaining the match.

**Scoring:** each priority is normalised to 0-1 across the matching colleges. One priority has weight 1.0; two priorities are weighted 0.6 / 0.4 in the order given.

## Notes

- `spring.jpa.hibernate.ddl-auto=none`: the schema lives in `database/schema.sql`.
- CORS allows `http://localhost:5173` (React dev server). Change with the `CORS_ORIGINS` env var.
- `RecommendationService` is the place to plug in the AI ranking service later.


## AI search (Ask AI tab)

Start the Python service first (see `ai-service/README.md`), then the backend and frontend as usual.
Browser -> `POST /api/recommendations/ai` (Spring Boot) -> `POST /rank` (FastAPI, port 8000).
Set `AI_SERVICE_URL` if the service runs elsewhere. The other two tabs do not need the AI service.

## Chatbot

A "Chat with us" button (bottom right) opens a chat. Needs `GEMINI_API_KEY` in `ai-service/.env`
(copy `ai-service/.env.example`). Browser -> `POST /api/chat` -> Python `POST /chat` -> Gemini, answering only from the
college data in the database.
