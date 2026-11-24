"""LangChain + Groq SLM chains for job extraction, cold-email generation, and LLM judging."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

try:
    from src.utils import clean_and_parse_json, clean_email_text
except ImportError:
    from utils import clean_and_parse_json, clean_email_text


DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


def load_env_files() -> None:
    """Load environment variables from project .env and user home ~/.env without overwriting."""
    load_dotenv(override=False)
    home_env = Path.home() / ".env"
    if home_env.exists():
        load_dotenv(dotenv_path=home_env, override=False)


def _format_links_for_prompt(links: Any) -> str:
    """Normalize retrieved link structures into a readable list for prompt injection."""
    if isinstance(links, str):
        return links
    if isinstance(links, list):
        lines: list[str] = []
        for item in links:
            if isinstance(item, dict):
                url = item.get("links") or item.get("link") or ""
                title = item.get("title") or ""
                if title and url:
                    lines.append(f"- {title}: {url}")
                elif url:
                    lines.append(f"- {url}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)
    return str(links)


class Chain:
    """Encapsulates Groq LLM chains for extraction, generation, and optional quality judging."""

    def __init__(self, model_name: str | None = None, api_key: str | None = None) -> None:
        load_env_files()
        self.model_name = model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        resolved_key = api_key or os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=0,
            max_tokens=None,
            timeout=60,
            max_retries=2,
            groq_api_key=resolved_key,
        )

    def extract_jobs(self, cleaned_page_data: str):
        """Extract structured role, experience, skills, and description from job text."""
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM JOB POSTING
            {page_data}
            Extract job details from this text and return a JSON array with one object.
            Use this exact JSON structure:
            [
              {{
                "role": "Job title",
                "experience": "Years of experience required",
                "skills": ["Skill 1", "Skill 2"],
                "description": "Brief job description"
              }}
            ]
            Return only valid JSON, nothing else.
            """
        )
        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={"page_data": cleaned_page_data})
        try:
            clean_and_parse_json(res.content)
        except OutputParserException:
            raise OutputParserException("Too big context. Please try again with shorter context.")
        return res

    def write_mail(self, job_description: dict[str, Any] | str, links: Any) -> str:
        """Generate a concise (<150 word) cold email incorporating retrieved portfolio links."""
        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION
            {job_description}

            ### RELEVANT PORTFOLIO LINKS
            {list_links}

            ### INSTRUCTION
            You are Anas Khan, Founder and CEO of Guruji-AI Pvt. Ltd. Guruji-AI is an AI, Software, and Consulting company that delivers
            tailored engineering solutions and seamless business process automation.
            Write a concise, clear, and coherent cold email in strictly under 150 words to the prospective client regarding the job above.
            Include at least one exact relevant URL from the RELEVANT PORTFOLIO LINKS above verbatim so the client can review our work.
            Remember you are Anas Khan, Founder and CEO of Guruji-AI Pvt. Ltd.

            Format the email starting with "Subject:" on the first line, followed by the greeting, body, and a signature ("Best regards, Anas Khan").
            Do not use markdown bullet lists or placeholders like [Client Link] instead of the actual URLs.

            ### EMAIL
            """
        )
        formatted_links = _format_links_for_prompt(links)
        chain_email = prompt_email | self.llm
        res = chain_email.invoke(
            {"job_description": str(job_description), "list_links": formatted_links}
        )
        return clean_email_text(res.content)

    def judge_email(
        self,
        *,
        job_text: str,
        retrieved_links: list[str],
        generated_email: str,
        judge_model: str | None = None,
    ) -> dict[str, Any] | None:
        """Score a generated email on a 1-5 rubric using a Groq judge model."""
        judge_llm = (
            self.llm
            if not judge_model or judge_model == self.model_name
            else ChatGroq(
                model=judge_model,
                temperature=0,
                max_tokens=300,
                timeout=60,
                max_retries=2,
                groq_api_key=os.getenv("GROQ_API_KEY"),
            )
        )
        prompt_judge = PromptTemplate.from_template(
            """
            Evaluate the cold email below against the target job description and retrieved portfolio links.
            Return ONLY a single JSON object with integer scores from 1 (poor) to 5 (excellent):
            {{
              "relevance": <1-5>,
              "groundedness": <1-5>,
              "clarity": <1-5>,
              "overall": <1-5>,
              "rationale": "<one short sentence>"
            }}

            Job Description:
            {job_text}

            Retrieved Portfolio Links:
            {retrieved_links}

            Generated Email:
            {generated_email}
            """
        )
        raw = (prompt_judge | judge_llm).invoke(
            {
                "job_text": job_text,
                "retrieved_links": ", ".join(retrieved_links),
                "generated_email": generated_email,
            }
        )
        match = re.search(r"\{[^{}]*\}", str(raw.content), flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            if all(k in parsed for k in ("relevance", "groundedness", "clarity", "overall")):
                return parsed
        except json.JSONDecodeError:
            return None
        return None
