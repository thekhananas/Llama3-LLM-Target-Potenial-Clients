import json
import re
from typing import Any

from bs4 import BeautifulSoup
import streamlit as st


def clean_and_parse_json(text: Any) -> dict[str, Any] | None:
    """Extract and validate a structured job posting JSON object from model output."""
    if not isinstance(text, str):
        text = str(text)

    # Remove Markdown code block fences
    cleaned = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```", "", cleaned).strip()

    candidates: list[Any] = []
    # Try parsing the full cleaned payload first (handles JSON arrays cleanly)
    try:
        candidates.append(json.loads(cleaned))
    except json.JSONDecodeError:
        pass

    # Fallback: extract first balanced JSON object
    pattern = r"\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}"
    match = re.search(pattern, cleaned, re.DOTALL)
    if match:
        try:
            candidates.append(json.loads(match.group(0)))
        except json.JSONDecodeError:
            pass

    for item in candidates:
        obj = item[0] if isinstance(item, list) and item else item
        if isinstance(obj, dict) and all(
            key in obj for key in ("role", "experience", "skills", "description")
        ):
            skills = obj.get("skills")
            if isinstance(skills, str):
                obj["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
            elif isinstance(skills, list):
                obj["skills"] = [str(s).strip() for s in skills if str(s).strip()]
            else:
                obj["skills"] = []
            return obj

    return None


def clean_text(text: str) -> str:
    """Strip HTML markup, non-printable characters, and excessive whitespace."""
    soup = BeautifulSoup(text, "html.parser")
    plain = soup.get_text()
    plain = "".join(char for char in plain if char.isprintable())
    return re.sub(r"\s+", " ", plain).strip()


def clean_email_text(text: str) -> str:
    """Normalize whitespace and enforce clean line breaks around email sections."""
    cleaned = " ".join(text.split())
    cleaned = cleaned.replace("Subject:", "\nSubject:")
    cleaned = re.sub(r"\s+(Dear\b)", r"\n\n\1", cleaned)
    cleaned = re.sub(r"\s+(Best regards,|Sincerely,|Warm regards,|Regards,)", r"\n\n\1", cleaned)
    return cleaned.strip()


def load_css():
    st.markdown("""
    <style>
    .stApp {
        max-width: 900px;
        margin: 0 auto;
    }
    .success-message {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .email-container {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 15px;
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)

