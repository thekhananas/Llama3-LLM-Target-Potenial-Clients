"""Offline unit and integration tests for LlamaMail multi-document RAG and telemetry."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from eval.evaluate import hit_rate_at_k, recall_at_k, reciprocal_rank, score_email_deterministic
from src.pipeline import run_llamamail_pipeline
from src.portfolio import DEFAULT_EMBEDDING_MODEL, Portfolio
from src.utils import clean_and_parse_json, clean_email_text


class FakeChain:
    """Deterministic stub SLM for offline pipeline integration tests."""

    model_name = "stub-slm-1b"

    def extract_jobs(self, cleaned_page_data: str):
        payload = [
            {
                "role": "Senior Python Engineer",
                "experience": "5 years",
                "skills": ["Python", "Django", "PostgreSQL", "Redis"],
                "description": cleaned_page_data[:120],
            }
        ]
        return SimpleNamespace(content=json.dumps(payload))

    def write_mail(self, job_description, links):
        first_link = links[0]["links"] if links else "https://www.thoughtworks.com/clients"
        return clean_email_text(
            f"Subject: Scalable Python & Django Engineering Support "
            f"Dear Hiring Team, At Guruji-AI Pvt. Ltd., we build resilient Python, Django, "
            f"and PostgreSQL systems. See our work at {first_link}. "
            f"Best regards, Anas Khan"
        )


class LlamaMailOfflineTests(unittest.TestCase):
    def test_clean_and_parse_json_handles_array_and_string_skills(self):
        raw = '```json\n[{"role":"Backend Dev","experience":"3 yrs","skills":"Python, FastAPI","description":"API work"}]\n```'
        parsed = clean_and_parse_json(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["role"], "Backend Dev")
        self.assertEqual(parsed["skills"], ["Python", "FastAPI"])

    def test_ir_metric_calculations(self):
        retrieved = ["doc_b", "doc_a", "doc_c"]
        relevant = ["doc_a", "doc_d"]
        self.assertEqual(recall_at_k(retrieved, relevant, 1), 0.0)
        self.assertEqual(recall_at_k(retrieved, relevant, 3), 0.5)
        self.assertEqual(hit_rate_at_k(retrieved, relevant, 2), 1.0)
        self.assertEqual(reciprocal_rank(retrieved, relevant), 0.5)

    def test_multi_document_portfolio_and_pipeline_telemetry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vs_dir = str(Path(tmpdir) / "vectorstore")
            log_file = Path(tmpdir) / "run_logs.jsonl"
            portfolio = Portfolio(persist_directory=vs_dir)
            stats = portfolio.load_portfolio(force_rebuild=True)

            self.assertEqual(stats["embedding_model"], DEFAULT_EMBEDDING_MODEL)
            self.assertEqual(stats["distance_space"], "cosine")
            self.assertEqual(stats["num_documents"], 12)
            self.assertGreater(stats["num_chunks"], 12)

            result = run_llamamail_pipeline(
                FakeChain(),
                portfolio,
                job_text="Seeking Python Django PostgreSQL Redis backend engineer.",
                top_k=3,
                log_path=log_file,
            )

            self.assertEqual(result["status"], "success")
            self.assertIn("doc_02_python_django_backend", result["retrieval"]["doc_ids"])
            self.assertGreater(result["timings_ms"]["end_to_end_ms"], 0.0)
            self.assertTrue(log_file.exists())

            lines = log_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            logged = json.loads(lines[0])
            self.assertEqual(logged["embedding_model"], DEFAULT_EMBEDDING_MODEL)
            self.assertEqual(logged["corpus_docs"], 12)

            rubric = score_email_deterministic(
                email=result["email"],
                retrieved_links=result["retrieval"]["links"],
                relevant_links=["https://www.thoughtworks.com/clients"],
            )
            self.assertEqual(rubric["deterministic_rubric_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
