import os
import json
import re
from bs4 import BeautifulSoup
import streamlit as st

def clean_and_parse_json(text: object) -> object:
    # Remove Markdown code block syntax
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'\s*```', '', text)

    # Find the first complete JSON object
    # This pattern matches balanced curly braces
    pattern = r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}'
    match = re.search(pattern, text, re.DOTALL)

    if match:
        json_str = match.group(0)
        try:
            parsed = json.loads(json_str)
            # Ensure we have a complete job listing
            if all(key in parsed for key in ['role', 'experience', 'skills', 'description']):
                return parsed
        except json.JSONDecodeError:
            pass
    return None

def clean_text(text):
    # Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()

    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable())

    # Remove excessive whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def clean_email_text(text):
    # Remove extra newlines and spaces
    cleaned = ' '.join(text.split())
    # Add proper line breaks for email formatting
    cleaned = cleaned.replace('Subject:', '\nSubject:')
    cleaned = cleaned.replace('Dear', '\n\nDear')
    cleaned = cleaned.replace('Best regards,', '\n\nBest regards,')
    return cleaned


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

