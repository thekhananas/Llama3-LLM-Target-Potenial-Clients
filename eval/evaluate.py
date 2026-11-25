"""Evaluation harness for LlamaMail: retrieval Recall@k/MRR, latency, and generation quality."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.chains import Chain, DEFAULT_GROQ_MODEL, load_env_files
from src.pipeline import run_llamamail_pipeline
from src.portfolio import Portfolio, cosine_similarity
from src.telemetry import summarize_latencies


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """Fraction of ground-truth relevant docs appearing in top-k unique retrieved docs."""
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    rel = set(relevant_ids)
    return len(top_k & rel) / len(rel)


def hit_rate_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """1.0 if at least one ground-truth relevant doc appears in top-k, else 0.0."""
    return 1.0 if (set(retrieved_ids[:k]) & set(relevant_ids)) else 0.0


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Reciprocal rank (1/rank) of the first relevant document, or 0.0 if absent."""
    rel = set(relevant_ids)
    for rank_idx, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in rel:
            return 1.0 / rank_idx
    return 0.0


def score_email_deterministic(
    *,
    email: str,
    retrieved_links: list[str],
    relevant_links: list[str],
) -> dict[str, Any]:
    """Compute objective, deterministic rubric checks for a generated cold email."""
    words = email.split()
    word_count = len(words)
    lower = email.lower()
    subject_present = "subject:" in lower
    under_150_words = 0 < word_count <= 150
    persona_present = ("anas khan" in lower) or ("guruji-ai" in lower) or ("guruji ai" in lower)
    retrieved_link_grounded = any(link in email for link in retrieved_links if link)
    relevant_link_grounded = any(link in email for link in relevant_links if link)

    checks = [
        subject_present,
        under_150_words,
        persona_present,
        retrieved_link_grounded,
        relevant_link_grounded,
    ]
    return {
        "word_count": word_count,
        "subject_present": subject_present,
        "under_150_words": under_150_words,
        "persona_present": persona_present,
        "retrieved_link_grounded": retrieved_link_grounded,
        "relevant_link_grounded": relevant_link_grounded,
        "deterministic_rubric_score": round(sum(1 for c in checks if c) / len(checks), 4),
    }


def _load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def run_retrieval_eval(
    *,
    dataset_path: Path,
    output_dir: Path,
    persist_dir: str = "vectorstore",
    top_k: int = 5,
    force_rebuild: bool = True,
) -> dict[str, Any]:
    """Evaluate offline multi-document ChromaDB retrieval (Recall@k, MRR, and latency)."""
    dataset = _load_dataset(dataset_path)
    portfolio = Portfolio(persist_directory=persist_dir)
    corpus_stats = portfolio.load_portfolio(force_rebuild=force_rebuild)

    # Warmup query so ONNX runtime session init doesn't skew the first sample
    portfolio.retrieve(["Python", "PostgreSQL"], top_k=top_k)

    ks = (1, 3, 5)
    recall_sums = {k: 0.0 for k in ks}
    hit_sums = {k: 0.0 for k in ks}
    rr_sum = 0.0
    latencies_ms: list[float] = []
    details: list[dict[str, Any]] = []

    for case in dataset:
        res = portfolio.retrieve(case["query_skills"], top_k=top_k)
        retrieved_ids = res["doc_ids"]
        relevant_ids = case["relevant_doc_ids"]
        lat = res["retrieval_ms"]
        latencies_ms.append(lat)

        case_recalls = {f"recall_at_{k}": round(recall_at_k(retrieved_ids, relevant_ids, k), 4) for k in ks}
        case_hits = {f"hit_rate_at_{k}": round(hit_rate_at_k(retrieved_ids, relevant_ids, k), 4) for k in ks}
        rr = round(reciprocal_rank(retrieved_ids, relevant_ids), 4)

        for k in ks:
            recall_sums[k] += case_recalls[f"recall_at_{k}"]
            hit_sums[k] += case_hits[f"hit_rate_at_{k}"]
        rr_sum += rr

        details.append(
            {
                "test_id": case["test_id"],
                "title": case["title"],
                "query_skills": case["query_skills"],
                "relevant_doc_ids": relevant_ids,
                "retrieved_doc_ids": retrieved_ids,
                "top_results": [
                    {
                        "rank": r["rank"],
                        "doc_id": r["doc_id"],
                        "best_similarity": r["best_similarity"],
                        "matched_chunks": r["matched_chunks"],
                        "link": r["link"],
                    }
                    for r in res["results"]
                ],
                "reciprocal_rank": rr,
                **case_recalls,
                **case_hits,
                "retrieval_ms": lat,
            }
        )

    n = max(len(dataset), 1)
    summary = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "num_queries": len(dataset),
        "corpus": corpus_stats,
        "metrics": {
            "recall_at_1": round(recall_sums[1] / n, 4),
            "recall_at_3": round(recall_sums[3] / n, 4),
            "recall_at_5": round(recall_sums[5] / n, 4),
            "hit_rate_at_1": round(hit_sums[1] / n, 4),
            "hit_rate_at_3": round(hit_sums[3] / n, 4),
            "hit_rate_at_5": round(hit_sums[5] / n, 4),
            "mrr": round(rr_sum / n, 4),
        },
        "retrieval_latency_ms": summarize_latencies(latencies_ms),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "retrieval_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (output_dir / "retrieval_eval_details.jsonl").open("w", encoding="utf-8") as fh:
        for row in details:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return summary


def run_e2e_eval(
    *,
    dataset_path: Path,
    output_dir: Path,
    model_name: str,
    judge_model: str | None,
    persist_dir: str = "vectorstore",
    top_k: int = 3,
) -> dict[str, Any]:
    """Run full SLM extraction + ChromaDB retrieval + email generation & quality evaluation."""
    load_env_files()
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env or ~/.env before running e2e evaluation.")

    dataset = _load_dataset(dataset_path)
    portfolio = Portfolio(persist_directory=persist_dir)
    corpus_stats = portfolio.load_portfolio(force_rebuild=False)
    llm = Chain(model_name=model_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = output_dir / "e2e_run_logs.jsonl"
    if run_log_path.exists():
        run_log_path.unlink()

    ks = (1, 3)
    e2e_recall_sums = {k: 0.0 for k in ks}
    e2e_rr_sum = 0.0
    valid_json_count = 0
    success_count = 0

    extract_latencies: list[float] = []
    retrieval_latencies: list[float] = []
    generation_latencies: list[float] = []
    e2e_latencies: list[float] = []

    rubric_scores: list[float] = []
    semantic_sims: list[float] = []
    word_counts: list[int] = []
    subject_ok = 0
    under_150_ok = 0
    persona_ok = 0
    retrieved_link_ok = 0
    relevant_link_ok = 0
    judge_scores: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    for case in dataset:
        case_record: dict[str, Any] = {
            "test_id": case["test_id"],
            "title": case["title"],
            "relevant_doc_ids": case["relevant_doc_ids"],
            "relevant_links": case["relevant_links"],
        }
        try:
            result = run_llamamail_pipeline(
                llm,
                portfolio,
                job_text=case["job_text"],
                top_k=top_k,
                log_path=run_log_path,
            )
            success_count += 1
            valid_json_count += 1

            timings = result["timings_ms"]
            extract_latencies.append(timings["extract_jobs_ms"])
            retrieval_latencies.append(timings["retrieval_ms"])
            generation_latencies.append(timings["generation_ms"])
            e2e_latencies.append(timings["end_to_end_ms"])

            retrieved_ids = result["retrieval"].get("doc_ids", [])
            retrieved_links = result["retrieval"].get("links", [])

            for k in ks:
                e2e_recall_sums[k] += recall_at_k(retrieved_ids, case["relevant_doc_ids"], k)
            rr = reciprocal_rank(retrieved_ids, case["relevant_doc_ids"])
            e2e_rr_sum += rr

            det = score_email_deterministic(
                email=result["email"],
                retrieved_links=retrieved_links,
                relevant_links=case["relevant_links"],
            )
            rubric_scores.append(det["deterministic_rubric_score"])
            word_counts.append(det["word_count"])
            subject_ok += int(det["subject_present"])
            under_150_ok += int(det["under_150_words"])
            persona_ok += int(det["persona_present"])
            retrieved_link_ok += int(det["retrieved_link_grounded"])
            relevant_link_ok += int(det["relevant_link_grounded"])

            vecs = portfolio.embed_texts([case["job_text"], result["email"]])
            sem_sim = round(cosine_similarity(vecs[0], vecs[1]), 4) if len(vecs) == 2 else 0.0
            semantic_sims.append(sem_sim)

            judge_res = None
            if judge_model:
                judge_res = llm.judge_email(
                    job_text=case["job_text"],
                    retrieved_links=retrieved_links,
                    generated_email=result["email"],
                    judge_model=judge_model,
                )
                if judge_res:
                    judge_scores.append(judge_res)

            case_record.update(
                {
                    "status": "success",
                    "extracted_skills": result["job_details"].get("skills", []),
                    "retrieved_doc_ids": retrieved_ids,
                    "retrieved_links": retrieved_links,
                    "e2e_recall_at_1": round(recall_at_k(retrieved_ids, case["relevant_doc_ids"], 1), 4),
                    "e2e_recall_at_3": round(recall_at_k(retrieved_ids, case["relevant_doc_ids"], 3), 4),
                    "e2e_reciprocal_rank": round(rr, 4),
                    "timings_ms": timings,
                    "deterministic_quality": det,
                    "semantic_similarity_job_to_email": sem_sim,
                    "judge_scores": judge_res,
                    "generated_email": result["email"],
                }
            )
        except Exception as exc:
            case_record.update({"status": "error", "error": str(exc)})

        details.append(case_record)

    n = max(len(dataset), 1)
    s_n = max(success_count, 1)

    judge_summary: dict[str, Any] | None = None
    if judge_scores:
        j_n = len(judge_scores)
        judge_summary = {
            "judge_model": judge_model,
            "num_scored": j_n,
            "mean_relevance_1_to_5": round(sum(float(j["relevance"]) for j in judge_scores) / j_n, 3),
            "mean_groundedness_1_to_5": round(sum(float(j["groundedness"]) for j in judge_scores) / j_n, 3),
            "mean_clarity_1_to_5": round(sum(float(j["clarity"]) for j in judge_scores) / j_n, 3),
            "mean_overall_1_to_5": round(sum(float(j["overall"]) for j in judge_scores) / j_n, 3),
        }

    summary = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "num_cases": len(dataset),
        "num_succeeded": success_count,
        "llm_model": model_name,
        "corpus": corpus_stats,
        "extraction_metrics": {
            "json_validity_rate": round(valid_json_count / n, 4),
        },
        "e2e_retrieval_metrics": {
            "recall_at_1": round(e2e_recall_sums[1] / n, 4),
            "recall_at_3": round(e2e_recall_sums[3] / n, 4),
            "mrr": round(e2e_rr_sum / n, 4),
        },
        "generation_quality": {
            "mean_deterministic_rubric_score": round(sum(rubric_scores) / s_n, 4) if rubric_scores else 0.0,
            "subject_present_rate": round(subject_ok / n, 4),
            "under_150_words_rate": round(under_150_ok / n, 4),
            "persona_present_rate": round(persona_ok / n, 4),
            "retrieved_link_grounded_rate": round(retrieved_link_ok / n, 4),
            "relevant_link_grounded_rate": round(relevant_link_ok / n, 4),
            "mean_word_count": round(sum(word_counts) / s_n, 2) if word_counts else 0.0,
            "mean_job_email_cosine_similarity": round(sum(semantic_sims) / s_n, 4) if semantic_sims else 0.0,
            "llm_judge": judge_summary,
        },
        "latency_ms": {
            "extract_jobs": summarize_latencies(extract_latencies),
            "retrieval": summarize_latencies(retrieval_latencies),
            "generation": summarize_latencies(generation_latencies),
            "end_to_end": summarize_latencies(e2e_latencies),
        },
    }

    (output_dir / "e2e_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (output_dir / "e2e_eval_details.jsonl").open("w", encoding="utf-8") as fh:
        for row in details:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LlamaMail retrieval and generation quality.")
    parser.add_argument("--mode", choices=["retrieval", "e2e", "all"], default="retrieval")
    parser.add_argument("--dataset", type=Path, default=Path("eval/test_dataset.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("benchmarks"))
    parser.add_argument("--persist-dir", type=str, default="vectorstore")
    parser.add_argument("--model", type=str, default=None, help="Groq model ID for e2e run")
    parser.add_argument("--judge-model", type=str, default=None, help="Optional Groq model ID for 1-5 judging")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    load_env_files()

    if args.mode in ("retrieval", "all"):
        ret_summary = run_retrieval_eval(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            persist_dir=args.persist_dir,
            top_k=args.top_k,
        )
        print("=== OFFLINE RETRIEVAL BENCHMARK ===")
        print(json.dumps(ret_summary, indent=2))

    if args.mode in ("e2e", "all"):
        model_name = args.model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        e2e_summary = run_e2e_eval(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            model_name=model_name,
            judge_model=args.judge_model,
            persist_dir=args.persist_dir,
            top_k=min(args.top_k, 3),
        )
        print("=== END-TO-END SLM + RAG BENCHMARK ===")
        print(json.dumps(e2e_summary, indent=2))


if __name__ == "__main__":
    main()
