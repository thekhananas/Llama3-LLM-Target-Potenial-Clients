"""Streamlit web interface for LlamaMail with retrieval inspection and latency metrics."""

import os
from pathlib import Path
import sys

# Ensure repo root is importable when launched via `streamlit run src/main.py`
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

from src.chains import Chain, DEFAULT_GROQ_MODEL
from src.pipeline import run_llamamail_pipeline
from src.portfolio import Portfolio
from src.utils import load_css


def create_streamlit_app(llm: Chain, portfolio: Portfolio) -> None:
    """Render the LlamaMail Streamlit app with live stage latencies and RAG trace."""
    st.set_page_config(layout="wide", page_title="LlamaMail: AI Cold Email Generator", page_icon="📧")
    load_css()

    corpus_stats = portfolio.load_portfolio()

    st.title("🤖 LlamaMail: AI Personalized Email Generator")
    st.write("Generate grounded cold emails from job postings using LangChain, Groq SLM, and multi-document ChromaDB RAG.")

    with st.sidebar:
        st.subheader("System Scope & Configuration")
        model_override = st.text_input("Groq Model ID", value=os.getenv("GROQ_MODEL", llm.model_name))
        top_k = st.slider("Top-K Portfolio Documents", min_value=1, max_value=6, value=3)
        st.caption(f"**Embedding Model:** `{corpus_stats['embedding_model']}`")
        st.caption(
            f"**ChromaDB Scope:** {corpus_stats['num_documents']} docs / "
            f"{corpus_stats['num_chunks']} chunks (cosine, size={corpus_stats['chunk_size']})"
        )

    input_mode = st.radio("Job Input Source", ["Job Posting URL", "Paste Job Description"], horizontal=True)

    col1, col2 = st.columns([2, 1])
    url_input = ""
    text_input = ""
    with col1:
        if input_mode == "Job Posting URL":
            url_input = st.text_input(
                "Enter the job posting URL:",
                value="https://www.coinbase.com/en-gb/careers/positions/5961292",
                help="Paste the URL of the job posting you want to analyze",
            )
        else:
            text_input = st.text_area(
                "Paste job description text:",
                height=140,
                placeholder="Paste job title, required skills, and responsibilities...",
            )

    with col2:
        st.write("")
        submit_button = st.button("Generate Email", type="primary", use_container_width=True)

    if submit_button:
        if model_override.strip() and model_override.strip() != llm.model_name:
            llm = Chain(model_name=model_override.strip())

        try:
            with st.spinner("Running LlamaMail RAG & generation pipeline..."):
                result = run_llamamail_pipeline(
                    llm,
                    portfolio,
                    url=url_input.strip() if input_mode == "Job Posting URL" else None,
                    job_text=text_input.strip() if input_mode == "Paste Job Description" else None,
                    top_k=top_k,
                )

            timings = result["timings_ms"]
            retrieval = result["retrieval"]

            st.success("Email generated successfully!", icon="✅")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("End-to-End Latency", f"{timings.get('end_to_end_ms', 0):.0f} ms")
            m2.metric("Job Extraction", f"{timings.get('extract_jobs_ms', 0):.0f} ms")
            m3.metric("ChromaDB Retrieval", f"{timings.get('retrieval_ms', 0):.0f} ms")
            m4.metric("Email Generation", f"{timings.get('generation_ms', 0):.0f} ms")

            st.subheader("📝 Generated Email")
            with st.expander("View Email", expanded=True):
                st.markdown(f'<div class="email-container">{result["email"]}</div>', unsafe_allow_html=True)

            st.subheader("📚 Retrieved Multi-Document Portfolio Matches")
            with st.expander("View Retrieved Documents & Similarity Scores", expanded=True):
                for item in retrieval.get("results", []):
                    st.markdown(
                        f"**#{item['rank']} {item['title']}** (`{item['doc_id']}`) — "
                        f"Cosine Similarity: `{item['best_similarity']:.4f}` | "
                        f"Matched Chunks: `{item['matched_chunks']}` | "
                        f"Link: {item['link']}"
                    )
                    st.caption(item["excerpt"][:260] + ("..." if len(item["excerpt"]) > 260 else ""))

            st.subheader("🔍 Job Analysis & Telemetry")
            with st.expander("View Extracted Job Details"):
                st.json(result["job_details"])
            with st.expander("View Stage Timings & Telemetry Record"):
                st.json(result["log_record"])

        except Exception as exc:
            st.error(f"An error occurred: {exc}")
            st.write("Check your GROQ_API_KEY, Groq model ID, or job URL and try again.")


if __name__ == "__main__":
    chain = Chain(model_name=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL))
    portfolio = Portfolio()
    create_streamlit_app(chain, portfolio)
