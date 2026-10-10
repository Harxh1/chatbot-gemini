"""Checks the scoring maths with a tiny fake embedder whose meaning we control.

Run:  python test_scoring.py
The fake embedder has three axes (fees, placement, rating). A sentence's vector is the count of
keywords from each axis, so we know exactly what "similar" means and can check the numbers by hand.
"""
import numpy as np

from scoring import Candidate, Ranker, softmax

AXES = [
    ("fee", "cheap", "afford", "budget", "low"),
    ("placement", "salary", "package", "job", "placements", "recruit"),
    ("rating", "rated", "reviews", "reputation", "academics"),
]


class FakeEmbedder:
    name = "fake-keyword-axes"

    def encode(self, texts):
        out = np.zeros((len(texts), 3 + 16), dtype=np.float32)
        for r, t in enumerate(texts):
            low = t.lower()
            for a, words in enumerate(AXES):
                out[r, a] = sum(low.count(w) for w in words)
            # words with no keyword meaning point in a text-specific direction, so unrelated texts are not "similar"
            out[r, 3 + sum(map(ord, t)) % 16] = 0.05
            out[r] /= np.linalg.norm(out[r])
        return out


def college(i, name, city, fees, lpa, rating):
    return Candidate(i, name, city, "Uttar Pradesh", "Private", fees, lpa, rating, None)


COLLEGES = [
    college(1, "Cheap Tech", "Agra", 50_000, 2.0, 3.0),
    college(2, "Placement Tech", "Noida", 300_000, 10.0, 4.0),
    college(3, "Rated Tech", "Lucknow", 200_000, 5.0, 4.8),
    college(4, "No Data Tech", "Greater Noida", 100_000, None, None),
]


def ranker():
    return Ranker(FakeEmbedder())


def test_weights_sum_to_one_and_follow_the_query():
    r = ranker()
    qv = r._embed(["I want cheap affordable budget college"])[0]
    w, _ = r.priority_weights(qv)
    assert abs(sum(w.values()) - 1) < 1e-9
    assert w["low_fees"] > 0.9, w


def test_unrelated_query_gives_equal_weights():
    r = ranker()
    qv = r._embed(["xyzzy"])[0]
    w, _ = r.priority_weights(qv)
    assert all(abs(v - 1 / 3) < 1e-9 for v in w.values()), w


def test_order_follows_priority():
    r = ranker()
    assert r.rank("cheap affordable budget", COLLEGES)["results"][0]["id"] == 1
    assert r.rank("high salary package job placements", COLLEGES)["results"][0]["id"] == 2
    assert r.rank("top rated good reviews reputation", COLLEGES)["results"][0]["id"] == 3


def test_missing_data_scores_zero_not_crash():
    out = ranker().rank("high salary package", COLLEGES)
    last = out["results"][-1]
    assert last["id"] in (1, 4)
    assert any("not available" in x for x in last["reasons"]) or last["id"] == 1


def test_city_in_query_boosts_that_city():
    r = ranker()
    out = r.rank("cheap budget college in Lucknow", COLLEGES)
    assert out["matched_places"] == ["Lucknow"]
    assert out["part_weights"]["location"] == 0.25
    lucknow = next(x for x in out["results"] if x["id"] == 3)
    assert lucknow["breakdown"]["location"] == 1.0
    others = [x for x in out["results"] if x["id"] != 3]
    assert all(x["breakdown"]["location"] == 0.0 for x in others)
    # naming the city lifts that college's score compared with not naming it
    plain = next(x for x in r.rank("cheap budget college", COLLEGES)["results"] if x["id"] == 3)
    assert lucknow["score"] > plain["score"]


def test_greater_noida_not_confused_with_noida():
    assert Ranker.find_places("colleges in Greater Noida", COLLEGES) == ["Greater Noida"]


def test_scores_between_0_and_100_and_limit():
    out = ranker().rank("cheap", COLLEGES, limit=2)
    assert len(out["results"]) == 2
    assert all(0 <= x["score"] <= 100 for x in out["results"])


def test_softmax_temperature():
    assert softmax([0.5, 0.3, 0.1], 0.15)[0] > softmax([0.5, 0.3, 0.1], 1.0)[0]


def test_empty_list():
    assert ranker().rank("cheap", [])["results"] == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(fns)} passed")
