import pandas as pd
import chromadb
from uuid import uuid4

class Portfolio:
    def __init__(self, file_path="data/tech_stack_sample.csv"):
        self.file_path = file_path
        self.data = pd.read_csv(file_path)
        self.chroma_client = chromadb.PersistentClient('vectorstore')
        self.collection = self.chroma_client.get_or_create_collection(name='portfolio')

    def load_portfolio(self):
        if not self.collection.count():
            for _, row in self.data.iterrows():
                self.collection.add(documents=row['Techstack'],
                                    metadatas={'links': row['Links']},
                                    ids=[str(uuid4())]
                                    )

    def query_links(self, skills: list):
        return self.collection.query(
            query_texts=skills,
            n_results=2,
        ).get('metadatas', [])
