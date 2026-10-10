"""Checks the chatbot plumbing with a fake Google response (no key or internet needed). Run: python test_chat.py"""
import chat

COLLEGES = [
    {"name": "Cheap Tech", "city": "Agra", "fees_per_year": 50000, "avg_placement_lpa": None, "rating": 3.0},
    {"name": "Big Tech", "city": "Noida", "fees_per_year": 300000, "avg_placement_lpa": 8.5, "rating": 4.2},
]


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body if body is not None else {
            "candidates": [{"content": {"parts": [{"text": "  Try Big Tech.  "}]}}]
        }

    def json(self):
        return self._body


class FakePost:
    """Stands in for requests.post and records what would have been sent to Google."""

    def __init__(self, response=None):
        self.calls = []
        self.response = response or FakeResponse()

    def __call__(self, url, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self.response


def test_prompt_has_data_and_dashes_for_missing():
    p = chat.build_system_prompt(COLLEGES)
    assert "Cheap Tech | Agra | 0.50 L | - | 3.0" in p
    assert "Big Tech | Noida | 3.00 L | 8.5 LPA | 4.2" in p


def test_answer_sends_cleaned_messages_and_returns_text():
    import os

    os.environ["GEMINI_API_KEY"] = "test-key"
    fake = FakePost()
    msgs = [
        {"role": "assistant", "content": "Hi!"},
        {"role": "user", "content": "best placements?"},
        {"role": "assistant", "content": "Big Tech."},
        {"role": "user", "content": "and cheapest?"},
    ]
    assert chat.answer(msgs, COLLEGES, post=fake) == "Try Big Tech."
    call = fake.calls[0]
    assert call["headers"]["x-goog-api-key"] == "test-key"
    assert "gemini" in call["url"]
    roles = [c["role"] for c in call["json"]["contents"]]
    assert roles == ["user", "model", "user"]  # leading assistant dropped, assistant -> model
    assert "Big Tech" in call["json"]["systemInstruction"]["parts"][0]["text"]


def test_consecutive_same_role_merged():
    out = chat.clean_messages([{"role": "user", "content": "a"}, {"role": "user", "content": "b"}])
    assert out == [{"role": "user", "content": "a\nb"}]


def test_must_end_with_user():
    try:
        chat.clean_messages([{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])
    except chat.ChatError as e:
        assert e.status == 400
    else:
        raise AssertionError("expected ChatError")


def test_missing_key_gives_clear_message():
    import os

    os.environ.pop("GEMINI_API_KEY", None)
    try:
        chat.answer([{"role": "user", "content": "hi"}], COLLEGES, post=FakePost())
    except chat.ChatError as e:
        assert e.status == 503 and ".env" in e.message
    else:
        raise AssertionError("expected ChatError")


def test_google_errors_become_friendly():
    import os

    os.environ["GEMINI_API_KEY"] = "bad"
    cases = [
        (400, {"error": {"message": "API key not valid. Please pass a valid API key."}}, "API key"),
        (404, {"error": {"message": "model not found"}}, "None of these models"),
        (429, {"error": {"message": "quota"}}, "quota"),
        (503, {"error": {"message": "overloaded"}}, "busy"),
    ]
    for status, body, expect in cases:
        try:
            chat.answer([{"role": "user", "content": "hi"}], COLLEGES, post=FakePost(FakeResponse(status, body)))
        except chat.ChatError as e:
            assert expect in e.message, (status, e.message)
        else:
            raise AssertionError("expected ChatError")


def test_falls_back_to_next_model_on_404_and_503():
    import os

    os.environ["GEMINI_API_KEY"] = "k"
    os.environ["GEMINI_MODEL"] = "bad-model"
    seen = []

    def post(url, headers, json, timeout):
        seen.append(url)
        if "bad-model" in url:
            return FakeResponse(404, {"error": {"message": "nope"}})
        if "gemini-flash-latest" in url:
            return FakeResponse(503, {"error": {"message": "busy"}})
        return FakeResponse()

    try:
        assert chat.answer([{"role": "user", "content": "hi"}], COLLEGES, post=post) == "Try Big Tech."
    finally:
        os.environ.pop("GEMINI_MODEL")
    assert "bad-model" in seen[0] and "gemini-flash-latest" in seen[1] and "flash-lite" in seen[2]


def test_bad_key_does_not_try_other_models():
    import os

    os.environ["GEMINI_API_KEY"] = "k"
    calls = []

    def post(url, headers, json, timeout):
        calls.append(url)
        return FakeResponse(400, {"error": {"message": "API key not valid"}})

    try:
        chat.answer([{"role": "user", "content": "hi"}], COLLEGES, post=post)
    except chat.ChatError:
        pass
    assert len(calls) == 1


def test_empty_candidates_gives_fallback_text():
    import os

    os.environ["GEMINI_API_KEY"] = "k"
    out = chat.answer([{"role": "user", "content": "hi"}], COLLEGES, post=FakePost(FakeResponse(200, {"candidates": []})))
    assert "rephrasing" in out


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(fns)} passed")
