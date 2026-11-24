"""Shared end-to-end LlamaMail execution pipeline with latency telemetry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_community.document_loaders import WebBaseLoader

try:
    from src.telemetry import DEFAULT_RUN_LOG_PATH, PipelineTimer, append_run_log, build_run_record
    from src.utils import clean_and_parse_json, clean_text
except ImportError:
    from telemetry import DEFAULT_RUN_LOG_PATH, PipelineTimer, append_run_log, build_run_record
    from utils import clean_and_parse_json, clean_text


def run_llamamail_pipeline(
    llm: Any,
    portfolio: Any,
    *,
    url: str | None = None,
    job_text: str | None = None,
    top_k: int = 3,
    log_path: str | Path | None = DEFAULT_RUN_LOG_PATH,
) -> dict[str, Any]:
    """Execute scraping/loading, extraction, ChromaDB retrieval, and email generation with timings."""
    timer = PipelineTimer()
    source_type = "url" if url else "text"
    retrieval: dict[str, Any] = {}
    job_details: dict[str, Any] | None = None
    email = ""
    extracted_skills: list[str] = []

    try:
        with timer.stage("scrape_ms"):
            if url:
                loader = WebBaseLoader([url])
                loaded = loader.load()
                if not loaded:
                    raise ValueError(f"No content retrieved from URL: {url}")
                cleaned_data = clean_text(loaded.pop().page_content)
            elif job_text:
                cleaned_data = clean_text(job_text)
            else:
                raise ValueError("Either 'url' or 'job_text' must be provided.")

        with timer.stage("load_portfolio_ms"):
            corpus_stats = portfolio.load_portfolio()

        with timer.stage("extract_jobs_ms"):
            raw_jobs = llm.extract_jobs(cleaned_data)
            job_details = clean_and_parse_json(raw_jobs.content)

        if not job_details:
            raise ValueError("Failed to extract valid job JSON (role, experience, skills, description).")

        extracted_skills = job_details.get("skills") or []
        query_input = extracted_skills if extracted_skills else job_details.get("description", "")

        with timer.stage("retrieval_ms"):
            retrieval = portfolio.retrieve(query_input, top_k=top_k)

        prompt_links = [
            {
                "doc_id": r["doc_id"],
                "title": r["title"],
                "links": r["link"],
                "similarity": r["best_similarity"],
            }
            for r in retrieval.get("results", [])
        ]

        with timer.stage("generation_ms"):
            email = llm.write_mail(job_details, prompt_links)

        timings = dict(timer.stages_ms)
        timings["end_to_end_ms"] = timer.total_ms()

        record = build_run_record(
            source_type=source_type,
            llm_model=getattr(llm, "model_name", "unknown"),
            embedding_model=corpus_stats.get("embedding_model", portfolio.embedding_model_name),
            corpus_docs=corpus_stats.get("num_documents", 0),
            corpus_chunks=corpus_stats.get("num_chunks", 0),
            timings_ms=timings,
            retrieved_doc_ids=retrieval.get("doc_ids", []),
            retrieved_links=retrieval.get("links", []),
            extracted_skills=extracted_skills,
            status="success",
        )
        if log_path is not None:
            append_run_log(record, log_path=log_path)

        return {
            "status": "success",
            "cleaned_data": cleaned_data,
            "job_details": job_details,
            "retrieval": retrieval,
            "email": email,
            "timings_ms": timings,
            "log_record": record,
        }

    except Exception as exc:
        timings = dict(timer.stages_ms)
        timings["end_to_end_ms"] = timer.total_ms()
        stats = portfolio.get_corpus_stats() if hasattr(portfolio, "get_corpus_stats") else {}
        record = build_run_record(
            source_type=source_type,
            llm_model=getattr(llm, "model_name", "unknown"),
            embedding_model=stats.get("embedding_model", "unknown"),
            corpus_docs=stats.get("num_documents", 0),
            corpus_chunks=stats.get("num_chunks", 0),
            timings_ms=timings,
            retrieved_doc_ids=retrieval.get("doc_ids", []),
            retrieved_links=retrieval.get("links", []),
            extracted_skills=extracted_skills,
            status="error",
            error=str(exc),
        )
        if log_path is not None:
            append_run_log(record, log_path=log_path)
        raise
