import os
import pandas as pd
from tqdm import tqdm

from llm_client.llm_client import LLMProcessor
from llm_client.document_vector_store import DocumentStore, Document
from llm_client.prompt_builder import PromptBuilder
from kme_doc import KMEDocument
from utils.structure_content import process_folder_concurrently
from config.settings import Settings

class DataIngestionPipeline:
    def __init__(self, settings: Settings, llm: LLMProcessor, doc_store: DocumentStore, summary_doc_store: DocumentStore):
        self.settings = settings
        self.llm = llm
        self.doc_store = doc_store
        self.summary_doc_store = summary_doc_store
        self.kme_vertaaltabel = pd.read_csv(os.path.join(self.settings.data_root, "kme_vertaaltabel.csv"), sep=';').set_index("KME_ID")

    def _check_for_new_content(self):
        filenames = [(k,v)[1].metadata['filename'] for k,v in self.doc_store.documents.items()]
        found_filenames = os.listdir('content')
        new_document_filenames = [filename for filename in found_filenames if filename not in filenames and filename.endswith(".pdf")]
        return new_document_filenames

    def _process_new_documents(self, new_document_ids: list[str]):
        new_content_doc = process_folder_concurrently(self.settings.content_folder, max_workers=8, filenames_to_process=new_document_ids)

        docs = []
        for filename, doc in new_content_doc.items():
            kme_tax = self.kme_vertaaltabel.loc[doc.km_number]
            metadata = {
                'filename': filename,
                'datum': doc.date,
                'BELASTINGSOORT': kme_tax['BELASTINGSOORT'],
                'PROCES_ONDERWERP': kme_tax['PROCES_ONDERWERP'],
                'PRODUCT_SUBONDERWERP': kme_tax['PRODUCT_SUBONDERWERP'],
                'VRAAG': kme_tax['VRAAG'],
            }
            new_doc = Document(doc.km_number, doc.title, doc.full_text, metadata)
            docs.append(new_doc)
        self.doc_store.add(docs)

    def _summarize_new_documents(self):
        summary_processor = PromptBuilder(template_path='prompt_templates', name='summarize')
        processed_docs = []

        for doc_id, doc in tqdm(self.doc_store.documents.items()):
            if doc_id not in self.summary_doc_store.documents.keys():
                try:
                    prompt = summary_processor.create_prompt(
                        document=doc.content,
                        question=doc.metadata['VRAAG'],
                        taxonomy_path=[
                            doc.metadata['BELASTINGSOORT'],
                            doc.metadata['PROCES_ONDERWERP'],
                            doc.metadata['PRODUCT_SUBONDERWERP']
                        ]
                    )
                    output = self.llm.process(prompt)
                    output_json = output.content
                    if summary_processor.verify_json(output_json):
                        new_summary = KMEDocument(id=doc_id, title=doc.title, content=output_json['content'], metadata=output_json['metadata'])
                        new_summary.metadata.update(doc.metadata)
                        new_summary.metadata["full_text"] = doc.content
                        processed_docs.append(new_summary)
                except Exception as e:
                    print(f"Error summarizing document {doc_id}: {e}")
                    continue

        if processed_docs:
            self.summary_doc_store.add(processed_docs)

    def run(self):
        print("Starting data ingestion pipeline...")
        new_document_ids = self._check_for_new_content()
        if new_document_ids:
            print(f"Found {len(new_document_ids)} new documents to process.")
            self._process_new_documents(new_document_ids)
        else:
            print("No new documents to process.")

        print("Checking for documents to summarize...")
        self._summarize_new_documents()
        print("Data ingestion pipeline finished.")
