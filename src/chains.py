import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from utils import clean_and_parse_json, clean_email_text, clean_text
from langchain_core.exceptions import OutputParserException

load_dotenv()

# get the GROQ_API_KEY
os.getenv('GROQ_API_KEY')


class Chain:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.2-1b-preview",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            groq_api_key=os.getenv('GROQ_API_KEY'))

    def extract_jobs(self, cleaned_page_data):
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPPED TEXT FROM WEBSITE
            {page_data}
            Extract job details from this text and return a JSON array with one object:
            Use this exact JSON structure:
            [
              {{
                "role": "Job title",
                "experience": "Years of experience required",
                "skills": ["Skill 1", "Skill 2", ...],
                "description": "Brief job description"
              }}
            ]
            Return only the JSON array, nothing else.
            """
        )
        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={'page_data': cleaned_page_data})
        try:
            parsed_json = clean_and_parse_json(res.content)

            print('parsed_json:', parsed_json)
        except OutputParserException:
            raise OutputParserException('Too big context. Please try again with shorted context.')
        return res

    def write_mail(self, job_description, links):
        print('writer_email:',job_description, links)
        propmpt_email = PromptTemplate.from_template(
            """
            ### JOB Description
            {job_description}

            ### INSTRUCTION
            You are Anas Khan, a Founder and CEO of Guruji-AI Pvt. Ltd. Guruji AI is an AI & Software and Consulting company that provides
            seamless integration of business processes through automated tools.
            Over the years, we have empowered various organizations with their vision through tailored solutions, fostering relationships and low cost.
            Your job is to write a concise, clear and coherent cold email in under 150 words to the client regarding the Job mentioned above and fulfilling
            their needs.
            Add the most relevant links from the following links to showcase Guruji-AI's vast performance across various domains: {list_links}.
            Remember you are Anas Khan, founder and CEO.

            Format the email with "Subject:" at the start, followed by the body of the email, and end with your signature.
            Do not use line breaks within paragraphs. Use a single line break between the subject, greeting, body paragraphs, and signature.

            ### EMAIL
            """
        )

        chain_email = propmpt_email | self.llm

        res = chain_email.invoke({'job_description': str(job_description), 'list_links': links})
        print('Is Email Correct:/n', clean_email_text(res.content))
        return clean_email_text(res.content)
