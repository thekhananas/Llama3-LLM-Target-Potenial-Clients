import streamlit as st
from langchain_community.document_loaders import WebBaseLoader

from chains import Chain
from portfolio import Portfolio
from utils import clean_and_parse_json
from utils import clean_text
from utils import load_css


def create_streamlit_app(llm, portfolio, clean_text, clean_and_parse_json):
    st.set_page_config(layout="wide", page_title="AI Cold Email Generator", page_icon="📧")
    load_css()

    st.title("🤖 AI Cold Email Generator")
    st.write("Generate personalized cold emails based on job descriptions and your portfolio.")

    col1, col2 = st.columns([2, 1])

    with col1:
        url_input = st.text_input("Enter the job posting URL:",
                                  value="https://www.coinbase.com/en-gb/careers/positions/5961292",
                                  help="Paste the URL of the job posting you want to analyze")

    with col2:
        submit_button = st.button("Generate Email", type="primary", use_container_width=True)

    if submit_button:
        try:
            with st.spinner("🔍 Analyzing job posting..."):
                loader = WebBaseLoader([url_input])
                data = clean_text(loader.load().pop().page_content)

            with st.spinner("📊 Loading portfolio data..."):
                portfolio.load_portfolio()

            with st.spinner("🧠 Extracting job details..."):
                jobs = llm.extract_jobs(data)
                job_valid_json = clean_and_parse_json(jobs.content)

            if not job_valid_json:
                st.error("Failed to extract job details. Please check the URL and try again.")
                return

            skills = job_valid_json['skills']

            with st.spinner("🔗 Finding relevant portfolio links..."):
                links = portfolio.query_links(skills)

            with st.spinner("✍️ Crafting your personalized email..."):
                email = llm.write_mail(job_valid_json, links)

            st.success("Email generated successfully!", icon="✅")

            st.subheader("📝 Generated Email")
            with st.expander("View Email", expanded=True):
                st.markdown(f'<div class="email-container">{email}</div>', unsafe_allow_html=True)

            # if st.button("📋 Copy to Clipboard"):
            #     st.write('<p class="success-message">Email copied to clipboard!</p>', unsafe_allow_html=True)
            #     st.session_state['clipboard'] = email

            st.subheader("🔍 Job Analysis")
            with st.expander("View Extracted Job Details"):
                st.json(job_valid_json)



        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.write("Please check the URL and try again. If the problem persists, contact support.")


if __name__ == "__main__":
    chain = Chain()
    portfolio = Portfolio()
    create_streamlit_app(chain, portfolio, clean_text, clean_and_parse_json)
