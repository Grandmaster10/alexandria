import time
import json
import math
import requests
from typing import Optional

BACKEND_URL      = "http://backend-api:3001"
SEARCH_URL       = f"{BACKEND_URL}/books/search/text"
BOOKS_URL        = f"{BACKEND_URL}/books"

EVAL_DATA_PATH   = "true_semantic_eval.json"

SEARCH_K = 10
REC_K    = 5

def load_cases(filepath: str) -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def ndcg(hits: list, k: int) -> float:
    dcg   = sum(h / math.log2(i + 2) for i, h in enumerate(hits[:k]))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(sum(hits), k)))
    return (dcg / ideal) if ideal > 0 else 0.0


def mrr(hits: list) -> float:
    for i, h in enumerate(hits):
        if h:
            return 1.0 / (i + 1)
    return 0.0


def genre_tokens(s: str) -> set:
    if not s or str(s).lower() in ("nan", "none", ""):
        return set()
    cleaned = str(s).lower().replace("/", " ").replace("&", " ").replace(",", " ")
    return {w.strip("[]'. ") for w in cleaned.split() if w.strip("[]'. ")}


def title_match(expected: str, returned: str) -> bool:
    e, r = expected.lower().strip(), returned.lower().strip()
    return e in r or r in e

def call_search(query: str) -> tuple:
    t0 = time.perf_counter()
    try:
        r = requests.post(SEARCH_URL, json={"query": query}, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", data.get("data", []))
    except Exception as e:
        print(f"    [SEARCH ERR] {e}")
        results = []
    return results, (time.perf_counter() - t0) * 1000

def fetch_catalogue() -> list:
    try:
        r = requests.get(BOOKS_URL, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [CATALOGUE ERR] {e}")
        return []

def call_recommendations(book_id: str) -> tuple:
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BOOKS_URL}/{book_id}/recommendations", timeout=30)
        r.raise_for_status()
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
    except Exception as e:
        print(f"    [REC ERR] {e}")
        results = []
    return results, (time.perf_counter() - t0) * 1000


def evaluate_semantic_search(test_cases: list, catalogue: list) -> dict:
    """
    Uses hand-crafted paraphrase queries from true_semantic_eval.json.
    Filters to only cases where the expected book is in the DB catalogue —
    can't penalise the model for a book it was never shown.
    """
    db_titles = {str(b.get("title", "")).lower().strip() for b in catalogue if b.get("title")}

    eligible = [
        item for item in test_cases
        if any(
            title_match(item["expected_book_id"], db_t)
            for db_t in db_titles
        )
    ]

    n = len(eligible)
    print(f"\n{'─'*64}")
    print(f"SEMANTIC SEARCH  (hand-crafted paraphrase queries)")
    print(f"{len(test_cases)} total queries  →  {n} eligible (book exists in DB)")
    print(f"Endpoint: POST /books/search/text")
    print(f"{'─'*64}\n")

    if n == 0:
        print("No eligible queries. Seed the DB first.")
        return {}

    total_latency = 0.0
    mrr_list, ndcg5_list, ndcg10_list = [], [], []
    hits_at_5 = hits_at_10 = 0

    for i, item in enumerate(eligible):
        results, latency = call_search(item["query"])
        total_latency += latency

        hits = [1 if title_match(item["expected_book_id"], b.get("title", "")) else 0
                for b in results]
        hits += [0] * max(0, SEARCH_K - len(hits))

        q_mrr = mrr(hits)
        mrr_list.append(q_mrr)
        ndcg5_list.append(ndcg(hits, 5))
        ndcg10_list.append(ndcg(hits, 10))
        if any(hits[:5]):  hits_at_5  += 1
        if any(hits[:10]): hits_at_10 += 1

        # Per-query diagnostic
        rank = next((j+1 for j, h in enumerate(hits) if h), None)
        status = f"rank {rank}" if rank else "MISS"
        print(f"  [{i+1:>2}/{n}] MRR={q_mrr:.2f}  {status:>7}  | {item['expected_book_id'][:45]}")

        if (i + 1) % 20 == 0:
            print(f"  {'─'*50}")
            print(f"  running MRR: {sum(mrr_list)/len(mrr_list):.4f}  (queries 1-{i+1})")
            print(f"  {'─'*50}")

    return {
        "total_queries":  n,
        "avg_latency_ms": total_latency / n,
        "mrr":            sum(mrr_list) / n,
        "recall_at_5":    hits_at_5  / n,
        "recall_at_10":   hits_at_10 / n,
        "ndcg_at_5":      sum(ndcg5_list)  / n,
        "ndcg_at_10":     sum(ndcg10_list) / n,
    }



def evaluate_recommender(test_cases: list, catalogue: list) -> dict:
    id_to_genre: dict = {b["id"]: str(b.get("type", "")) for b in catalogue if b.get("id")}
    title_index: list = [
        (str(b.get("title", "")).lower().strip(), b["id"])
        for b in catalogue if b.get("id") and b.get("title")
    ]

    print(f"\n{'─'*64}")
    print(f"BOOK RECOMMENDER  (genre-overlap relevance)")
    print(f"Catalogue: {len(catalogue)} books  |  {len(test_cases)} test cases to probe")
    print(f"Endpoint: GET /books/:id/recommendations")
    print(f"{'─'*64}\n")

    total_latency = 0.0
    evaluated = 0
    mrr_list, ndcg5_list, prec5_list, rec5_list = [], [], [], []

    for item in test_cases:
        query_title  = item["expected_book_id"].lower().strip()
        query_tokens = genre_tokens(item.get("category", ""))

        book_id: Optional[str] = None
        for db_title, db_id in title_index:
            if title_match(query_title, db_title):
                book_id = db_id
                break

        if not book_id:
            continue

        recs, latency = call_recommendations(book_id)
        total_latency += latency
        evaluated += 1

        hits = []
        for rec in recs[:REC_K]:
            rec_id     = rec.get("id", "")
            rec_genre  = id_to_genre.get(rec_id) or rec.get("type", "")
            rec_tokens = genre_tokens(rec_genre)
            hits.append(1 if (query_tokens & rec_tokens) else 0)
        hits += [0] * max(0, REC_K - len(hits))

        total_rel = sum(hits)
        mrr_list.append(mrr(hits))
        ndcg5_list.append(ndcg(hits, REC_K))
        prec5_list.append(total_rel / REC_K)
        rec5_list.append(total_rel / max(1, total_rel))

        if evaluated % 50 == 0:
            print(f"{evaluated} evaluated  |  Precision@5 so far: {sum(prec5_list)/len(prec5_list):.1%}")

    if not evaluated:
        print("No test books found in the DB.")
        return {}

    return {
        "books_evaluated": evaluated,
        "avg_latency_ms":  total_latency / evaluated,
        "mrr":             sum(mrr_list)   / evaluated,
        "precision_at_5":  sum(prec5_list) / evaluated,
        "recall_at_5":     sum(rec5_list)  / evaluated,
        "ndcg_at_5":       sum(ndcg5_list) / evaluated,
    }

def _bar(v: float, w: int = 24) -> str:
    filled = int(round(max(0.0, min(1.0, v)) * w))
    return f"[{'█' * filled}{'░' * (w - filled)}]"


def print_report(sm: dict, rm: dict):
    W = 68
    print("\n" + "=" * W)
    print(f"{'ALEXANDRIA — EVALUATION REPORT':^{W}}")
    print("=" * W)

    if sm:
        print(f"SEMANTIC SEARCH  (paraphrase queries → real model quality)")
        print(f"{'─'*62}")
        print(f"{'Eligible Queries':<32} {sm['total_queries']:>6}")
        print(f"{'Avg Latency':<32} {sm['avg_latency_ms']:>6.1f} ms\n")
        rows = [
            ("MRR",       sm["mrr"],          "Avg rank of correct book (0–1, ≥0.5 is good)"),
            ("Recall@5",  sm["recall_at_5"],  "% queries: correct book in top 5"),
            ("Recall@10", sm["recall_at_10"], "% queries: correct book in top 10"),
            ("NDCG@5",    sm["ndcg_at_5"],    "Rank-weighted quality at 5 (0–1)"),
            ("NDCG@10",   sm["ndcg_at_10"],   "Rank-weighted quality at 10 (0–1)"),
        ]
        print(f"{'Metric':<14} {'Value':>8}   {'Bar':<26}  Notes")
        print(f"{'─'*62}")
        for label, val, note in rows:
            disp = f"{val:.1%}" if "Recall" in label else f"{val:.4f}"
            print(f"  {label:<14} {disp:>8}   {_bar(val):<26}  {note}")

    if rm:
        print(f"BOOK RECOMMENDER  (genre-overlap relevance)")
        print(f"{'─'*62}")
        print(f"{'Books Evaluated':<32} {rm['books_evaluated']:>6}")
        print(f"{'Avg Latency':<32} {rm['avg_latency_ms']:>6.1f} ms\n")
        rows = [
            ("MRR",         rm["mrr"],           "Rank of first genre-relevant rec (0–1)"),
            ("Precision@5", rm["precision_at_5"],"Fraction of top-5 recs sharing query genre"),
            ("Recall@5",    rm["recall_at_5"],   "Genre-relevant recall within top 5"),
            ("NDCG@5",      rm["ndcg_at_5"],     "Weighted genre-overlap quality at 5"),
        ]
        print(f"  {'Metric':<14} {'Value':>8}   {'Bar':<26}  Notes")
        print(f"  {'─'*62}")
        for label, val, note in rows:
            disp = f"{val:.1%}" if any(x in label for x in ("Precision", "Recall")) else f"{val:.4f}"
            print(f"  {label:<14} {disp:>8}   {_bar(val):<26}  {note}")

    print("=" * W + "\n")

def run_evaluation():
    print("\nLoading evaluation files...")
    eval_cases = load_cases(EVAL_DATA_PATH)
    print(f"  True semantic queries: {len(eval_cases)}")

    print("\nFetching DB catalogue...")
    catalogue = fetch_catalogue()
    print(f"  {len(catalogue)} books in the database")

    sm = evaluate_semantic_search(eval_cases, catalogue)
    rm = evaluate_recommender(eval_cases, catalogue)

    print_report(sm, rm)


if __name__ == "__main__":
    run_evaluation()