from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, List, Dict, Any
from tqdm import tqdm
import pandas as pd

from llm_client.document_vector_store import Document, DocumentStore
from llm_client.prompt_builder import PromptBuilder
from llm_client.llm_client import LLMProcessor
from kme_doc import KMEDocument

KME_TABLE: pd.DataFrame = pd.read_csv("data/kme_vertaaltabel.csv", sep=";").set_index("KME_ID")

def check_for_new_content(kme_documents: pd.DataFrame, doc_store: DocumentStore) -> List[pd.Series]:
    """Return rows uit kme_documents die nog niet in doc_store zitten."""
    return [row for row in kme_documents.itertuples() if not doc_store.contains(row.km_nummer)]


def add_new_documents_to_docstore(
    kme_documents: pd.DataFrame,
    doc_store: DocumentStore,
    kme_table: Optional[pd.DataFrame] = None,
) -> Tuple[int, List[str]]:
    """
    Zet nieuwe KME-rows om naar Document en voeg ze toe aan doc_store.
    Retourneert (aantal_toegevoegd, ontbrekende_kme_ids)
    """
    table = kme_table if kme_table is not None else KME_TABLE
    new_rows = check_for_new_content(kme_documents, doc_store)  # bugfix: doc_store doorgeven

    docs: List[Document] = []
    missing: List[str] = []

    for row in new_rows:
        km_id = row.km_nummer
        if km_id in table.index:
            tax = table.loc[km_id]
            metadata = {
                "filename": row.source_file,
                "id": row.id,
                "private_answer_html": row.private_answer_html,
                "private_answer": row.private_answer_text,
                "public_answer_html": row.publicAnswer_html,
                "public_answer": row.publicAnswer_text,
                "BELASTINGSOORT": tax["BELASTINGSOORT"],
                "PROCES_ONDERWERP": tax["PROCES_ONDERWERP"],
                "PRODUCT_SUBONDERWERP": tax["PRODUCT_SUBONDERWERP"],
                "VRAAG": tax["VRAAG"],
            }
            docs.append(Document(km_id, row.title, row.full_text, metadata))
        else:
            missing.append(km_id)

    if docs:
        doc_store.add(docs)

    return len(docs), missing


def summarize_new_documents(
    *,
    doc_store: DocumentStore,
    summary_doc_store: DocumentStore,
    prompt_builder: PromptBuilder,   
    llm: LLMProcessor,               
    KMEDocument_cls,                
    max_workers: int = 16,
    start: int = 0,                
    count: Optional[int] = None,     
    reasoning_effort: str = "low",
    show_progress: bool = True,
) -> Dict[str, int]:
    """
    Threaded + streaming: voegt elk resultaat direct toe aan summary_doc_store.
    Eenvoudig, robuust, en snel genoeg voor I/O-bound LLM-calls.
    """
    items = list(doc_store.documents.items())
    end = None if count is None else start + max(0, count)
    items_slice = items[start:end]

    existing = set(summary_doc_store.documents.keys())
    todo = [(doc_id, doc) for doc_id, doc in items_slice if doc_id not in existing]
    if not todo:
        return {"submitted": 0, "added": 0, "skipped_existing": len(items_slice)}

    def _one(doc_id: str, doc: Document) -> Optional[KMEDocument]:
        md = doc.metadata or {}
        prompt = prompt_builder.create_prompt(
            document=doc.content,
            question=md.get("VRAAG"),
            taxonomy_path=[
                md.get("BELASTINGSOORT"),
                md.get("PROCES_ONDERWERP"),
                md.get("PRODUCT_SUBONDERWERP"),
            ],
        )
        res = llm.process(prompt, reasoning_effort=reasoning_effort)
        out = res.content

        # Optioneel: verifiëren indien beschikbaar
        if hasattr(prompt_builder, "verify_json") and callable(prompt_builder.verify_json):
            if not prompt_builder.verify_json(out):
                return None

        if not isinstance(out, dict) or "content" not in out:
            return None

        merged_md = {**(out.get("metadata") or {}), **md, "full_text": doc.content}
        return KMEDocument_cls(
            id=doc_id,
            title=getattr(doc, "title", None),
            content=out["content"],
            metadata=merged_md,
        )

    added = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_one, doc_id, doc): doc_id for doc_id, doc in todo}
        iterator = as_completed(futs)
        if show_progress:
            iterator = tqdm(iterator, total=len(futs), desc="Summarizing")

        for fut in iterator:
            try:
                km = fut.result()
            except Exception:
                km = None  # blijf doorgaan zoals je originele 'continue'

            if km is not None:
                summary_doc_store.add([km])
                added += 1

    return {"submitted": len(todo), "added": added, "skipped_existing": len(items_slice) - len(todo)}
