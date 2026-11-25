# LlamaMail: AI-Powered Job Application Assistant

## 📌 Overview

The AI Cold Email Generator is an innovative tool designed to streamline the process of creating personalized cold emails for job applications. By leveraging AI technology, this application analyzes job postings and generates tailored emails that highlight relevant skills and experiences.

![AI Job Email Generator Demo](demo/AI_Personalized_Email_Generator.png)

## 🎥 Demo

Check out our demo video to see the AI Cold Job Email Generator in action:

[Watch the Demo Video](demo/Demo_Llama3.2_Job_Email_Generator.mov)

## ✨ Features

- **Job Analysis**: Automatically extracts key information from job postings.
- **Skill Matching**: Identifies relevant skills from your portfolio.
- **Personalized Email Generation**: Creates customized cold emails based on the job requirements and your skills.
- **User-Friendly Interface**: Easy-to-use Streamlit-based web application.

## 🛠 Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/Llama3-LLM-Target-Potenial-Clients
   cd Llama3-LLM-Target-Potenial-Clients
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   Create a `.env` file in the root directory and add your API keys:
   ```
   GROQ_API_KEY=your_llama_api_key
   ```

## 💻 Usage

1. Start the Streamlit app:
   ```
   streamlit run src/main.py
   ```

2. Open your web browser and navigate to the URL provided by Streamlit (usually `http://localhost:8501`).

3. Enter the URL of a job posting you're interested in.

4. Click "Generate Email" and wait for the AI to analyze the job and create your personalized cold email.

5. Review the generated email, job analysis, and relevant portfolio links.

6. Copy the email content and use it as a starting point for your job application.

## 📊 Verified Architecture, Benchmarks & Evaluation

### Retrieval & Telemetry Scope
- **Embedding Model:** Explicit `sentence-transformers/all-MiniLM-L6-V2 (Chroma ONNXMiniLM_L6_V2)` (`384`-dim, `cosine` HNSW space)
- **Multi-Document ChromaDB Corpus:** `12` portfolio case-study documents in `data/portfolio_docs/` split into `38` chunks (`chunk_size=500`, `chunk_overlap=80`) via `RecursiveCharacterTextSplitter`, with document-level Reciprocal Rank Fusion (RRF) aggregation
- **LLM / SLM:** `openai/gpt-oss-20b` via Groq API (`GROQ_MODEL` env var configurable; updated from deprecated `llama-3.2-1b-preview`)
- **Latency Instrumentation:** Stage-by-stage (`scrape_ms`, `load_portfolio_ms`, `extract_jobs_ms`, `retrieval_ms`, `generation_ms`, `end_to_end_ms`) displayed in Streamlit and logged to `benchmarks/run_logs.jsonl`

### Verified Benchmark Results (`eval/test_dataset.json`, 16 queries)
- **Offline Retrieval (`benchmarks/retrieval_eval.json`):**
  - `Recall@1`: `0.9375` | `Recall@3`: `1.0` | `Recall@5`: `1.0` | `MRR`: `1.0`
  - Retrieval latency: `525.7 ms` mean (`548.18 ms` p50, `695.81 ms` p95)
- **End-to-End SLM + RAG (`benchmarks/e2e_eval.json`, `openai/gpt-oss-20b`):**
  - Extraction JSON validity: `1.0` (`16/16`)
  - E2E Retrieval (using extracted skills): `Recall@1`: `0.9375` | `Recall@3`: `1.0` | `MRR`: `1.0`
  - Deterministic generation rubric (`Subject:`, `<=150` words, persona, grounded link): `1.0` (`mean_word_count`: `100.56`)
  - Semantic alignment (job-to-email cosine similarity): `0.7774`
  - LLM-as-a-judge (`openai/gpt-oss-120b`, `n=5` parsed): `4.0 / 5.0` overall (`4.8` relevance, `3.4` groundedness, `4.4` clarity)
  - End-to-end latency: `12949.78 ms` mean (`14747.86 ms` p50, `19402.85 ms` p95)

### Reproducing Tests & Benchmarks
```bash
# Offline unit & integration tests
.venv/bin/python -m unittest discover -s tests -v

# Offline multi-document retrieval benchmark (Recall@k, MRR, retrieval latency)
.venv/bin/python eval/evaluate.py --mode retrieval

# Live end-to-end SLM + RAG benchmark (requires GROQ_API_KEY)
.venv/bin/python eval/evaluate.py --mode e2e --model openai/gpt-oss-20b --judge-model openai/gpt-oss-120b
```

## 📁 Project Structure

```
Llama3-LLM-Target-Potenial-Clients/
├── src/
│   ├── main.py
│   ├── chains.py
│   ├── portfolio.py
│   └── utils.py
├── data/
│   └── tech_stack_sample.csv
├── demo/
│   ├── demo_screenshot.png
│   └── AI_Cold_Email_Generator_Demo.mp4
├── .gitignore
├── requirements.txt
└── README.md
```

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check [issues page](https://github.com/thekhananas/) if you want to contribute.

## 📝 License

This project is [MIT](https://choosealicense.com/licenses/mit/) licensed.

## 🙏 Acknowledgements

- Llama (Meta AI) and Groq for providing the language model API
- LangChain for allowing to chain different agents
- Streamlit for the excellent web app framework
- All contributors and supporters of this project
