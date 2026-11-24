"""Multi-document ChromaDB portfolio index and semantic retriever for LlamaMail."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd

try:
    from src.telemetry import PipelineTimer
except ImportError:
    from telemetry import PipelineTimer


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-V2 (Chroma ONNXMiniLM_L6_V2)"
DEFAULT_DOCS_DIR = "data/portfolio_docs"
DEFAULT_CSV_PATH = "data/tech_stack_sample.csv"
DEFAULT_COLLECTION_NAME = "portfolio_docs"


def _parse_markdown_doc(path: Path) -> dict[str, str]:
    """Parse a portfolio markdown document with YAML-style key/value frontmatter."""
    raw = path.read_text(encoding="utf-8").strip()
    meta: dict[str, str] = {
        "doc_id": path.stem,
        "title": path.stem.replace("_", " ").title(),
        "domain": "Software Engineering",
        "tech_stack": "",
        "link": "",
    }
    body = raw
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, flags=re.DOTALL)
    if match:
        header_block, body = match.group(1), match.group(2).strip()
        for line in header_block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip().lower()] = value.strip()
    meta["body"] = body
    meta["source_file"] = path.name
    return meta


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class Portfolio:
    """ChromaDB-backed multi-document portfolio store with explicit ONNX MiniLM embeddings."""

    def __init__(
        self,
        file_path: str = DEFAULT_CSV_PATH,
        docs_dir: str | None = DEFAULT_DOCS_DIR,
        persist_directory: str = "vectorstore",
        collection_name: str = DEFAULT_COLLECTION_NAME,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
    ) -> None:
        self.file_path = file_path
        self.docs_dir = Path(docs_dir) if docs_dir else None
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embedding_model_name = DEFAULT_EMBEDDING_MODEL
        self.embedding_function = ONNXMiniLM_L6_V2()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n## ", "\n\n", "\n", ". ", " ", ""],
        )

        self.chroma_client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self._get_or_create_collection()

        self.num_documents = 0
        self.num_chunks = 0
        self._corpus_signature = ""

        # Keep CSV dataframe accessible for backward compatibility if present
        csv_path = Path(self.file_path)
        self.data = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()

    def _get_or_create_collection(self, metadata: dict[str, Any] | None = None):
        collection_meta = {
            "hnsw:space": "cosine",
            "embedding_model": self.embedding_model_name,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
        if metadata:
            collection_meta.update(metadata)
        return self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata=collection_meta,
        )

    def _build_chunks_from_corpus(self) -> tuple[list[str], list[dict[str, Any]], list[str], str, int]:
        """Load and chunk portfolio markdown docs (or fall back to CSV rows)."""
        hasher = hashlib.sha256()
        hasher.update(f"{self.embedding_model_name}|{self.chunk_size}|{self.chunk_overlap}".encode("utf-8"))

        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []

        md_files = sorted(self.docs_dir.glob("*.md")) if (self.docs_dir and self.docs_dir.exists()) else []
        if md_files:
            for path in md_files:
                hasher.update(path.name.encode("utf-8"))
                hasher.update(path.read_bytes())
                doc = _parse_markdown_doc(path)
                chunks = self.text_splitter.split_text(doc["body"]) or [doc["body"]]
                total_chunks = len(chunks)
                for idx, chunk in enumerate(chunks):
                    contextual_chunk = (
                        f"Title: {doc['title']}\n"
                        f"Domain: {doc['domain']}\n"
                        f"Tech Stack: {doc['tech_stack']}\n\n"
                        f"{chunk}"
                    )
                    documents.append(contextual_chunk)
                    metadatas.append(
                        {
                            "doc_id": doc["doc_id"],
                            "title": doc["title"],
                            "domain": doc["domain"],
                            "tech_stack": doc["tech_stack"],
                            "links": doc["link"],
                            "chunk_index": idx,
                            "total_chunks": total_chunks,
                            "source_file": doc["source_file"],
                            "source_type": "portfolio_markdown",
                        }
                    )
                    ids.append(f"{doc['doc_id']}::chunk_{idx}")
            num_docs = len(md_files)
        else:
            if self.data.empty:
                return [], [], [], hasher.hexdigest(), 0
            for idx, row in self.data.iterrows():
                tech = str(row["Techstack"])
                link = str(row["Links"])
                doc_id = f"csv_row_{idx:02d}"
                hasher.update(f"{doc_id}|{tech}|{link}".encode("utf-8"))
                documents.append(f"Tech Stack: {tech}")
                metadatas.append(
                    {
                        "doc_id": doc_id,
                        "title": tech,
                        "domain": "Portfolio Stack",
                        "tech_stack": tech,
                        "links": link,
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "source_file": Path(self.file_path).name,
                        "source_type": "csv_row",
                    }
                )
                ids.append(f"{doc_id}::chunk_0")
            num_docs = len(self.data)

        return documents, metadatas, ids, hasher.hexdigest(), num_docs

    def load_portfolio(self, force_rebuild: bool = False) -> dict[str, Any]:
        """Ensure the ChromaDB collection matches the current multi-document corpus."""
        documents, metadatas, ids, signature, num_docs = self._build_chunks_from_corpus()
        self.num_documents = num_docs
        self.num_chunks = len(documents)
        self._corpus_signature = signature

        existing_meta = self.collection.metadata or {}
        existing_sig = existing_meta.get("corpus_signature")
        existing_count = self.collection.count()

        if not force_rebuild and existing_count == len(documents) and existing_sig == signature:
            return self.get_corpus_stats()

        try:
            self.chroma_client.delete_collection(name=self.collection_name)
        except Exception:
            pass

        self.collection = self._get_or_create_collection(
            metadata={
                "corpus_signature": signature,
                "num_documents": num_docs,
                "num_chunks": len(documents),
            }
        )
        if documents:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        return self.get_corpus_stats()

    def get_corpus_stats(self) -> dict[str, Any]:
        """Return metadata describing the indexed vector store scope."""
        return {
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model_name,
            "distance_space": "cosine",
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "num_documents": self.num_documents,
            "num_chunks": self.num_chunks or self.collection.count(),
        }

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed arbitrary texts using the portfolio's explicit ONNX embedding model."""
        if not texts:
            return []
        raw_vectors = self.embedding_function(texts)
        return [[float(x) for x in vec] for vec in raw_vectors]

    def retrieve(
        self,
        query_input: list[str] | str,
        top_k: int = 5,
        n_results_per_query: int = 12,
    ) -> dict[str, Any]:
        """Retrieve and rank unique portfolio documents from chunk-level ChromaDB hits."""
        timer = PipelineTimer()
        with timer.stage("load_if_empty"):
            if not self.collection.count():
                self.load_portfolio()

        if isinstance(query_input, str):
            skills = [s.strip() for s in query_input.split(",") if s.strip()]
            combined_query = query_input.strip()
        else:
            skills = [str(s).strip() for s in query_input if str(s).strip()]
            combined_query = ", ".join(skills)

        if not combined_query:
            return {
                "results": [],
                "links": [],
                "doc_ids": [],
                "retrieval_ms": 0.0,
                **self.get_corpus_stats(),
            }

        queries = [combined_query] + (skills if len(skills) > 1 else [])
        total_chunks = self.collection.count()
        n_fetch = min(max(n_results_per_query, top_k * 4), max(total_chunks, 1))

        with timer.stage("chroma_query"):
            raw = self.collection.query(
                query_texts=queries,
                n_results=n_fetch,
                include=["documents", "metadatas", "distances"],
            )

        # Fuse chunk rankings across the combined query (weight 1.5) and individual skills
        k_rrf = 15.0
        doc_scores: dict[str, dict[str, Any]] = {}

        all_ids = raw.get("ids") or []
        all_docs = raw.get("documents") or []
        all_metas = raw.get("metadatas") or []
        all_dists = raw.get("distances") or []

        for q_idx in range(len(queries)):
            weight = 1.5 if q_idx == 0 else 0.75 / max(len(skills), 1)
            q_ids = all_ids[q_idx] if q_idx < len(all_ids) else []
            q_docs = all_docs[q_idx] if q_idx < len(all_docs) else []
            q_metas = all_metas[q_idx] if q_idx < len(all_metas) else []
            q_dists = all_dists[q_idx] if q_idx < len(all_dists) else []

            seen_in_query: set[str] = set()
            doc_rank_in_query = 0

            for chunk_id, chunk_text, meta, dist in zip(q_ids, q_docs, q_metas, q_dists):
                doc_id = str(meta.get("doc_id") or chunk_id)
                similarity = round(max(0.0, 1.0 - float(dist)), 4)

                entry = doc_scores.setdefault(
                    doc_id,
                    {
                        "doc_id": doc_id,
                        "title": meta.get("title", doc_id),
                        "domain": meta.get("domain", ""),
                        "tech_stack": meta.get("tech_stack", ""),
                        "link": meta.get("links", ""),
                        "rrf_score": 0.0,
                        "best_similarity": similarity,
                        "matched_chunk_ids": set(),
                        "best_excerpt": chunk_text,
                        "best_chunk_index": meta.get("chunk_index", 0),
                    },
                )
                entry["matched_chunk_ids"].add(chunk_id)

                if similarity > entry["best_similarity"]:
                    entry["best_similarity"] = similarity
                    entry["best_excerpt"] = chunk_text
                    entry["best_chunk_index"] = meta.get("chunk_index", 0)

                if doc_id not in seen_in_query:
                    seen_in_query.add(doc_id)
                    doc_rank_in_query += 1
                    entry["rrf_score"] += weight / (k_rrf + doc_rank_in_query)

        ranked = sorted(
            doc_scores.values(),
            key=lambda item: (item["rrf_score"], item["best_similarity"]),
            reverse=True,
        )[:top_k]

        results: list[dict[str, Any]] = []
        for rank_idx, item in enumerate(ranked, start=1):
            results.append(
                {
                    "rank": rank_idx,
                    "doc_id": item["doc_id"],
                    "title": item["title"],
                    "domain": item["domain"],
                    "tech_stack": item["tech_stack"],
                    "link": item["link"],
                    "score": round(item["rrf_score"], 5),
                    "best_similarity": item["best_similarity"],
                    "matched_chunks": len(item["matched_chunk_ids"]),
                    "best_chunk_index": item["best_chunk_index"],
                    "excerpt": item["best_excerpt"],
                }
            )

        return {
            "results": results,
            "links": [r["link"] for r in results if r["link"]],
            "doc_ids": [r["doc_id"] for r in results],
            "retrieval_ms": timer.stages_ms.get("chroma_query", 0.0),
            **self.get_corpus_stats(),
        }

    def query_links(self, skills: list[str] | str, top_k: int = 3) -> list[dict[str, Any]]:
        """Retrieve top-k portfolio links and titles matching the given skills."""
        retrieved = self.retrieve(skills, top_k=top_k)
        return [
            {
                "doc_id": item["doc_id"],
                "title": item["title"],
                "links": item["link"],
                "similarity": item["best_similarity"],
            }
            for item in retrieved["results"]
        ]
