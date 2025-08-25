import re
import logging
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from operator import itemgetter
from typing import Optional # Added for type hinting

# --- Setup Logging ---
# Configure logger to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class StructuredDocument:
    """A data class to store structured information from a document.

    :param km_number: The KM-number of the document, defaults to None
    :type km_number: str | None
    :param date: The date found in the document, defaults to None
    :type date: str | None
    :param title: The title of the document, defaults to None
    :type title: str | None
    :param private_info: The content under 'Private information' or 'Privéantwoord', defaults to None
    :type private_info: str | None
    :param interne_info: The content under 'Interne informatie', defaults to None
    :type interne_info: str | None
    :param tags: The tags associated with the document, defaults to None
    :type tags: str | None
    :param source_file: The filename of the source PDF, defaults to None
    :type source_file: str | None
    :param full_text: The full text of the source PDF
    :type full_text: str | None
    """
    km_number: str | None = None
    date: str | None = None
    title: str | None = None
    private_info: str | None = None
    interne_info: str | None = None
    tags: str | None = None
    source_file: str | None = None
    full_text:str | None = None

class PDFProcessor:
    def __init__(self):
        self.section_headers = {
            "private_info": ["Private information", "Privéantwoord"],
            "interne_info": ["Interne informatie"],
            "tags": ["Tags"]
        }

    def parse_page_with_pymupdf(self, page: fitz.Page) -> dict:
        extracted_data = {}
        page_dict = page.get_text("dict")

        blocks = page_dict.get("blocks", [])
        blocks.sort(key=lambda b: b['bbox'][1])

        all_lines = []
        for block in blocks:
            for line in block.get("lines", []):
                line_text = "".join(span['text'] for span in line['spans'])
                all_lines.append({'bbox': line['bbox'], 'text': line_text})

        all_lines.sort(key=lambda x: x['bbox'][1])
        extracted_data['full_text'] = " ".join([line['text'] for line in all_lines])

        date_km_anchor = None
        section_anchors = []

        for line in all_lines:
            text = line['text']
            if re.search(r'\d{2}/\d{2}/\d{4}', text) and re.search(r'\bKM\d+\b', text, re.IGNORECASE):
                date_km_anchor = {'y0': line['bbox'][1], 'text': text}
            else:
                for key, aliases in self.section_headers.items():
                    if any(alias in text for alias in aliases):
                        section_anchors.append({'key': key, 'y0': line['bbox'][1], 'y1': line['bbox'][3]})
                        break

        # Extract date / KM if present on this page
        if date_km_anchor:
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_km_anchor['text'])
            km_match = re.search(r'\b(KM\d+)\b', date_km_anchor['text'], re.IGNORECASE)
            extracted_data['date'] = date_match.group(1) if date_match else None
            extracted_data['km_number'] = km_match.group(1).upper() if km_match else None
        else:
            extracted_data['date'] = None
            extracted_data['km_number'] = None

        def clean_chars(text: str) -> str:
            text = text.replace('\xa0', ' ')
            text = re.sub(r'[\ue000-\uf8ff]', '', text).strip()
            return text

        # Title only determinable if we have the date/KM anchor on this page
        if date_km_anchor:
            title_lines = [
                clean_chars(line['text'])
                for line in all_lines
                if line['bbox'][1] < date_km_anchor['y0'] and clean_chars(line['text']) != ''
            ]
            extracted_data['title'] = title_lines[0] if title_lines else None
        else:
            extracted_data['title'] = None

        # Capture sections between anchors
        all_anchors = sorted(section_anchors, key=itemgetter('y0'))
        for i, anchor in enumerate(all_anchors):
            start_y = anchor['y1']
            end_y = all_anchors[i + 1]['y0'] if i + 1 < len(all_anchors) else page.rect.height

            content_lines = [
                line['text'] for line in all_lines
                if line['bbox'][1] >= start_y and line['bbox'][3] <= end_y
            ]
            content = "\n".join(content_lines).strip()
            if content:
                extracted_data[anchor['key']] = content

        return extracted_data

    def process_single_file(self, pdf_path: Path) -> tuple[str, StructuredDocument] | None:
        logging.info(f"Starting processing for: {pdf_path.name}")
        try:
            with fitz.open(pdf_path) as doc:
                if not len(doc):
                    logging.warning(f"'{pdf_path.name}' contains no pages.")
                    return None

                # Accumulator for the whole document
                acc: dict[str, str | None] = {
                    'km_number': None,
                    'date': None,
                    'title': None,
                    'private_info': '',
                    'interne_info': '',
                    'tags': '',
                    'full_text': '',
                    'source_file': pdf_path.name,
                }

                for page_index in range(len(doc)):
                    page = doc.load_page(page_index)
                    page_data = self.parse_page_with_pymupdf(page)

                    # First non-empty wins for these:
                    for k in ('km_number', 'date', 'title'):
                        if acc[k] in (None, '') and page_data.get(k):
                            acc[k] = page_data[k]

                    # Concatenate section content
                    for k in ('private_info', 'interne_info', 'tags'):
                        v = page_data.get(k)
                        if v:
                            if acc[k]:
                                acc[k] += "\n"
                            acc[k] += v

                    # Full text of the whole doc
                    ft = page_data.get('full_text')
                    if ft:
                        if acc['full_text']:
                            acc['full_text'] += "\n"
                        acc['full_text'] += ft

                # Normalize empty strings to None where the dataclass expects Optional[str]
                for k in ('private_info', 'interne_info', 'tags', 'full_text'):
                    if isinstance(acc[k], str) and acc[k].strip() == '':
                        acc[k] = None

                return (pdf_path.name, StructuredDocument(**acc))

        except Exception as e:
            logging.error(f"Critical error processing '{pdf_path.name}': {e}", exc_info=True)
            return None

def process_folder_concurrently(
    folder_path: str,
    max_workers: int = 4,
    filenames_to_process: Optional[list[str]] = None
) -> dict[str, StructuredDocument]:
    """Processes PDF files in a folder concurrently using a thread pool.

    :param folder_path: The path to the folder containing PDF files.
    :type folder_path: str
    :param max_workers: The maximum number of threads to use, defaults to 4
    :type max_workers: int
    :param filenames_to_process: An optional list of specific filenames to process.
                                 If None, all PDFs in the folder are processed.
    :type filenames_to_process: Optional[list[str]]
    :return: A dictionary of filenames and their structured data.
    :rtype: dict[str, StructuredDocument]
    """
    processor = PDFProcessor()
    path = Path(folder_path)
    if not path.is_dir():
        logging.error(f"Error: Folder not found at '{folder_path}'")
        return {}

    pdf_files = list(path.glob('*.pdf'))
    
    # --- MODIFICATION START ---
    # If a specific list of filenames is provided, filter the list.
    if filenames_to_process:
        logging.info(f"Filtering based on provided list of {len(filenames_to_process)} filenames.")
        filenames_set = set(filenames_to_process)
        pdf_files = [p for p in pdf_files if p.name in filenames_set]

    if not pdf_files:
        logging.warning(f"No PDF files found to process in '{folder_path}'.")
        return {}

    all_documents = {}
    logging.info(f"Found {len(pdf_files)} PDF files to process. Starting concurrent processing...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pdf = {executor.submit(processor.process_single_file, pdf_path): pdf_path for pdf_path in pdf_files}
        
        progress_bar = tqdm(as_completed(future_to_pdf), total=len(pdf_files), desc="Processing PDFs")
        
        for future in progress_bar:
            try:
                result = future.result()
                if result:
                    filename, doc_data = result
                    all_documents[filename] = doc_data
            except Exception as exc:
                pdf_path = future_to_pdf[future]
                logging.error(f"'{pdf_path.name}' generated an exception in the main loop: {exc}")

    return all_documents