# AI ranking service

A small FastAPI app. Spring Boot sends it the colleges and the student's sentence; it returns a ranked list.

## Run

```bash
cd ai-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000
```

First start downloads the `all-MiniLM-L6-v2` model (about 90 MB, once). Check it: `curl localhost:8000/health`.
If the model cannot be downloaded the service falls back to a simple word-matching embedder (`"model": "hashing-fallback"`
in the response). `AI_EMBEDDER=hash` forces that fallback. Tests: `python test_scoring.py`.

## How a college is scored

```
final = A * priority_fit + B * wording_fit + C * location_fit        (each part 0..1, shown as 0..100)
```

| Part | Meaning | Normal | City named |
|---|---|---|---|
| A priority_fit | how good the college is on what the student cares about | 0.70 | 0.55 |
| B wording_fit | similarity of the request to the college's name/city/description | 0.30 | 0.20 |
| C location_fit | 1 if the request names the college's city, else 0 | 0.00 | 0.25 |

**priority_fit** = `w_fees * fee_score + w_place * placement_score + w_rating * rating_score`

* `fee_score = 1 - (fee - min) / (max - min)` (cheapest = 1)
* `placement_score = (lpa - min) / (max - min)` (missing = 0)
* `rating_score = rating / 5` (missing = 0)
* min/max are taken over the colleges being compared (after the state/course filter).

**The weights `w_*` come from the transformer.** The request and a few example sentences for each priority are turned into
384-number vectors. Cosine similarity of the request to each priority's closest example gives `s_fees, s_place, s_rating`.
Then `w_i = exp(s_i / T) / sum_j exp(s_j / T)` with `T = 0.15`, so the weights add up to 1 and the clearest priority
dominates. If the request is not close to any priority (best similarity under 0.25) all three weights are 1/3.

**wording_fit** is the cosine similarity between the request vector and the college text vector, stretched to 0..1
across the colleges being compared.

Tune `PRIORITY_EXAMPLES`, `TEMPERATURE`, `MIN_SIGNAL`, `PARTS_*` at the top of `scoring.py`.

## Chatbot (Gemini API)

The "Chat with us" button calls `POST /api/chat` (Spring Boot) -> `POST /chat` (this service) -> Gemini.
Spring Boot sends the conversation plus all colleges; the model is told to answer only from that data.

```bash
printf 'GEMINI_API_KEY=\n' > .env   # then open .env and paste your key after the =
uvicorn main:app --port 8000        # restart after editing .env
```

`curl localhost:8000/health` shows `"chat_enabled": true` once the key is found. The key stays in this folder (`.env` is
git-ignored) and is never sent to the browser. Without a key the rest of the app works and the chat shows a clear message.
`GEMINI_MODEL` in `.env` changes the model. Tests (no key needed): `python test_chat.py`.
