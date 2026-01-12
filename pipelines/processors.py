from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, List, Dict, Any
from tqdm import tqdm
import pandas as pd
import tqdm

from contentcreatie.llm_client.document_store import Document, DocumentStore
from contentcreatie.llm_client.prompt_builder import PromptBuilder
from contentcreatie.llm_client.llm_client import LLMProcessor
from .kme_doc import KMEDocument
from logging import getLogger
# from contentcreatie.config.logger import get_logger

logger = getLogger("extract")

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
    new_rows = check_for_new_content(kme_documents, doc_store) 

    docs: List[Document] = []
    missing: List[str] = []

    for row in tqdm.tqdm(new_rows):
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
                "BELASTINGSOORT": row.BELASTINGSOORT,
                "PROCES_ONDERWERP": row.PROCES_ONDERWERP,
                "PRODUCT_SUBONDERWERP": row.PRODUCT_SUBONDERWERP,
                "VRAAG": tax.VRAAG,
            }
            docs.append(KMEDocument(km_id, row.title, row.full_text, metadata))
        else:
            missing.append(km_id)

    if docs:
        doc_store.add(docs)

    return len(docs), missing


def summarize_new_documents(
    *,
    doc_store: DocumentStore,
    prompt_builder: PromptBuilder,
    llm: LLMProcessor,
    max_workers: int = 16,
    start: int = 0,
    count: Optional[int] = None,
    reasoning_effort: str = "low",
    show_progress: bool = True,
) -> Dict[str, int]:
    """
    Summarizes documents that lack a 'summary' in their metadata using a threaded executor.
    
    This version includes robust logging and detailed error reporting to track
    validation failures, key errors, and exceptions during processing.

    :param doc_store: DocumentStore, The document store containing KMEDocuments.
    :param prompt_builder: PromptBuilder, Used to create prompts for the LLM.
    :param llm: LLMProcessor, The LLM processing unit.
    :param max_workers: int, Maximum number of threads, defaults to 16
    :param start: int, The starting index of documents to process, defaults to 0
    :param count: Optional[int], The maximum number of documents to process, defaults to None
    :param reasoning_effort: str, The reasoning effort for the LLM, defaults to "low"
    :param show_progress: bool, Whether to display a tqdm progress bar, defaults to True
    :return: Dict[str, int], A dictionary with detailed statistics of the run.
    """
    items = list(doc_store.documents.items())
    end = None if count is None else start + max(0, count)
    items_slice = items[start:end]

    # Filter documents that haven't been summarized yet
    todo = []
    for doc_id, doc in items_slice:
        if not doc.metadata or "summary" not in doc.metadata:
            todo.append((doc_id, doc))
    
    stats = {
        "submitted": len(todo),
        "added": 0,
        "skipped_existing": len(items_slice) - len(todo),
        "validation_errors": 0,
        "key_errors": 0,
        "exceptions": 0,
    }

    if not todo:
        return stats

    def _one(doc_id: str, doc: KMEDocument) -> Tuple[str, str, Any]:
        """
        Internal worker function.
        
        Returns a tuple: (doc_id, status, result)
        Status: "success", "validation_error", "key_error", "exception"
        Result: KMEDocument on success, raw LLM output or Exception on failure.
        """
        try:
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

            # 1. Check JSON validation
            if hasattr(prompt_builder, "verify_json") and callable(prompt_builder.verify_json):
                if not prompt_builder.verify_json(out):
                    logger.warning(
                        f"Validation error for doc {doc_id}. LLM output: {str(out)[:200]}..."
                    )
                    return (doc_id, "validation_error", out)

            # 2. Check for type and 'content' key
            if not isinstance(out, dict) or "content" not in out:
                logger.warning(
                    f"Key/Type error for doc {doc_id}. 'content' key missing or 'out' is not a dict. LLM output: {str(out)[:200]}..."
                )
                return (doc_id, "key_error", out)

            # Success: create the updated document
            updated_metadata = {
                **md, 
                "summary": out["content"], 
                "tags": out.get("metadata", {}).get("Tags",{})
            }
            
            updated_doc = KMEDocument(
                id=doc.id,
                title=doc.title,
                content=doc.content,
                metadata=updated_metadata
            )
            doc_store.add([updated_doc],save=False,update_index=False) 
            logger.info(f"Finished processing {doc_id}")
            return (doc_id, "success", updated_doc)

        except Exception as e:
            logger.error(f"Exception processing doc {doc_id}: {e}", exc_info=True)
            return (doc_id, "exception", e)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_one, doc_id, doc): doc_id for doc_id, doc in todo}
        
        iterator = as_completed(futs)
        if show_progress:
            iterator = tqdm.tqdm(iterator, total=len(futs), desc="Summarizing")

        for fut in iterator:
            try:
                # _one catches its own exceptions, so fut.result() should not fail
                doc_id, status, data = fut.result()
                
                if status == "success":
                    stats["added"] += 1
                elif status == "validation_error":
                    stats["validation_errors"] += 1
                elif status == "key_error":
                    stats["key_errors"] += 1
                elif status == "exception":
                    stats["exceptions"] += 1
            
            except Exception as e:
                # This catches a critical failure in the future itself
                doc_id = futs[fut] 
                logger.critical(f"A future failed unexpectedly for doc {doc_id}: {e}", exc_info=True)
                stats["exceptions"] += 1 

    return stats