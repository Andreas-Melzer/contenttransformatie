"""
Utility functions for extracting content from a ZIP file containing HTML documents.
"""
import os
import re
import zipfile
import html
import tqdm
from typing import Any, Dict, List, Optional

# We need BeautifulSoup for HTML parsing
from bs4 import BeautifulSoup
from contentcreatie.config.settings import Settings
from contentcreatie.config.paths import paths

settings = Settings()




TAG_ID = re.compile(r"\[\[--ContentED\.([a-z0-9]+)\|\|([^|]+)\|\|([^|]+)\|\|([^-\]]+)--\]\]", re.IGNORECASE)


def extract_content_links(html_text: str) -> List[Dict[str, str]]:
    """Extract content links from HTML text.

    :param html_text: str, HTML text containing content links.
    :return: List[Dict[str, str]], List of dictionaries with content link information.
    """
    out = []
    for m in TAG_ID.finditer(html_text or ""):
        out.append({
            "content_id": m.group(1),
            "link_title": m.group(2),
            "km_id": m.group(3),
            "type": m.group(4)
        })
    return out


def strip_html(html_text: Optional[str]) -> str:
    """Strip HTML tags from text and convert to plain text.

    :param html_text: Optional[str], HTML text to strip.
    :return: str, Plain text with HTML tags removed.
    """
    if not html_text:
        return ""
    
    # quick & decent: remove tags; preserve <br> as newline first
    t = html_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    t = re.sub(r"<\/p\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(re.sub(r"\n{3,}", "\n\n", t)).strip()


def extract_html(filename: str, html_content: str) -> Dict[str, Any]:
    """Extract content from an HTML document.

    :param filename: str, Name of the source file.
    :param html_content: str, The raw HTML content.
    :return: Dict[str, Any], Dictionary with extracted content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract ID (from <title> tag)
    doc_id = soup.title.string if soup.title else None

    # Extract Title (from <div class="title">)
    title_div = soup.find('div', class_='title')
    title = title_div.get_text(strip=True) if title_div else None
    
    def get_answer_html(line_class: str) -> str:
        """Helper to extract inner HTML from answer divs."""
        answer_div = soup.find('div', class_=line_class)
        if not answer_div:
            return ""
        
        # Clone the div to avoid modifying the original soup
        answer_div_clone = BeautifulSoup(str(answer_div), 'html.parser')
        
        # Find the header class (e.g., "private-header")
        header_class = line_class.replace('-line', '-header')
        header = answer_div_clone.find('div', class_=header_class)
        
        if header:
            header.decompose() # Remove the header
        
        # Get the remaining inner HTML of the main container
        # We find the div again *within the clone* to get the root
        inner_div = answer_div_clone.find('div', class_=line_class)
        return inner_div.decode_contents().strip() if inner_div else ""

    private_html = get_answer_html('private-line')
    public_html = get_answer_html('public-line')

    private_text = strip_html(private_html)
    public_text = strip_html(public_html)

    # Extract Tags
    tags_list = []
    tags_div = soup.find('div', class_='tags-line')
    if tags_div:
        # Clone to be safe
        tags_div_clone = BeautifulSoup(str(tags_div), 'html.parser')
        header = tags_div_clone.find('div', class_='tags-header')
        if header:
            header.decompose()
        
        tags_text = tags_div_clone.get_text(strip=True)
        if tags_text:
            tags_list = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

    rec = {
        "source_file": filename,
        "id": doc_id,
        "title": title,
        "private_answer_html": private_html,
        "private_answer_text": private_text,
        "publicAnswer_html": public_html,
        "publicAnswer_text": public_text,
        "links_in_private_answer": extract_content_links(private_html or ""),
        'full_text': "Public Answer: " + public_text + ' Private Answer: ' + private_text,
        "tags": tags_list
    }
    
    return rec


def get_all_html_docs(file_name: str) -> Dict[str, Any]:
    """Extract all HTML documents from a single ZIP file.

    :param file_name: str, The name of the zip file in the content_folder.
    :return: Dict[str, Any], Dictionary mapping internal file names to extracted document records.
    """
    zip_path = paths.content_folder / file_name
    docs = {}
    
    if not os.path.exists(zip_path):
        print(f"Error: File not found at {zip_path}")
        return {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Find all HTML files
        members = [m for m in zf.namelist() if m.lower().endswith(".html")]
        for name in tqdm.tqdm(members):
            try:
                with zf.open(name, "r") as fh:
                    raw = fh.read()
                    # Decode HTML content using utf-8-sig
                    html_content = raw.decode('utf-8-sig')
                
                # Use the HTML extraction function
                doc_record = extract_html(name, html_content)
                docs[name] = doc_record
                
            except Exception as e:
                print(f"Error processing {name} in {zip_path}: {e}")
    
    return docs