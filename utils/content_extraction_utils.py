"""
Utility functions for extracting content from JAR files containing JSON documents.
"""
import os
import glob
import json
import re
import zipfile
import html
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from config.settings import Settings

settings = Settings()


def as_list(x: Any) -> List[Any]:
    """Convert a value to a list.

    :param x: Value to convert to list. Can be None, list, or dict with "____listValues" key.
    :return: List representation of the input value.
    """
    if x is None:
        return []
    
    if isinstance(x, list):
        return x
    
    # Some lists are stored under "____listValues"
    if isinstance(x, dict) and "____listValues" in x:
        return x["____listValues"]
    
    return [x]


def get_field_value_list(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract field value list from a document.

    :param doc: Document dictionary containing entityHolderMap.
    :return: List of field value dictionaries.
    """
    try:
        return as_list(doc["entityHolderMap"]["nl-NL"]["dynamicEntity"]["fieldValueList"]["____listValues"])
    except KeyError:
        return []


def find_field(field_values: List[Dict[str, Any]], wanted_prefix: str) -> Optional[Any]:
    """Find a field in a list of field values based on a prefix.

    :param field_values: List of field value dictionaries.
    :param wanted_prefix: Prefix to match against fieldId.
    :return: Value of the matching field, or None if not found.
    """
    for fv in field_values:
        fid = fv.get("fieldId", "")
        if fid.startswith(wanted_prefix):
            val = fv.get("value")
            # ClobDynamicValue: nested value under value["value"]
            if isinstance(val, dict) and "value" in val:
                return val["value"]
            return val
    return None


TAG_ID = re.compile(r"\[\[--ContentED\.([a-z0-9]+)\|\|([^|]+)\|\|([^|]+)\|\|([^-\]]+)--\]\]", re.IGNORECASE)


def extract_content_links(html_text: str) -> List[Dict[str, str]]:
    """Extract content links from HTML text.

    :param html_text: HTML text containing content links.
    :return: List of dictionaries with content link information.
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

    :param html_text: HTML text to strip.
    :return: Plain text with HTML tags removed.
    """
    if not html_text:
        return ""
    
    # quick & decent: remove tags; preserve <br> as newline first
    t = html_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    t = re.sub(r"<\/p\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(re.sub(r"\n{3,}", "\n\n", t)).strip()


def get_id(doc: Dict[str, Any]) -> Optional[str]:
    """Extract ID from a document.

    :param doc: Document dictionary.
    :return: Document ID, or None if not found.
    """
    try:
        return doc["entityHolderMap"]["nl-NL"]["dynamicEntity"]["id"]
    except KeyError:
        # some files also mirror an "id" at top-level of the nl-NL object
        return doc.get("entityHolderMap", {}).get("nl-NL", {}).get("id")


def get_tags(doc: Dict[str, Any], field_name: str) -> List[str]:
    """Extract tags from a document based on field name.

    :param doc: Document dictionary.
    :param field_name: Name of the field to extract tags from (e.g. "topic", "agentskill", "knowledgeBase").
    :return: List of tag values.
    """
    # e.g. "topic", "agentskill", "knowledgeBase"
    fields = get_field_value_list(doc)
    val = find_field(fields, f"{field_name}::::")
    
    # Tag sets come wrapped; walk to selection list
    if isinstance(val, dict):
        try:
            sel = val["value"]["tagSetSelectionList"]["____listValues"]
            return list(sel) if isinstance(sel, list) else []
        except Exception:
            return []
    
    return []


def get_comment_list(doc: Dict[str, Any]) -> List[str]:
    """Extract comment list from a document.

    :param doc: Document dictionary.
    :return: List of comments.
    """
    try:
        return as_list(doc["entityHolderMap"]["nl-NL"]["commentList"]["____listValues"])
    except KeyError:
        return []


def get_all_json_docs(pattern: str = "*scrubbed.jar", content_type: str = "geel") -> Dict[str, Any]:
    """Extract all JSON documents from JAR files.

    :param pattern: Glob pattern to match JAR files.
    :param content_type: Content type directory to search in.
    :return: Dictionary mapping file names to document dictionaries.
    """
    jar_paths = glob.glob(str(settings.content_folder / content_type / pattern))
    docs = {}
    
    for jar_path in jar_paths:
        with zipfile.ZipFile(jar_path, "r") as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(".json")]
            for name in members:
                try:
                    with zf.open(name, "r") as fh:
                        raw = fh.read()
                    doc = json.loads(raw)
                    docs[name] = doc
                except Exception as e:
                    print(str(e))
    
    return docs


def extract_json(filename: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """Extract content from a JSON document.

    :param filename: Name of the source file.
    :param doc: Document dictionary.
    :return: Dictionary with extracted content.
    """
    fvals = get_field_value_list(doc)
    
    title = find_field(fvals, "title::::")
    public_html = find_field(fvals, "publicAnswer::::")
    private_html = find_field(fvals, "privateAnswer::::")
    
    # some files mirror privateAnswer at nl-NL level too; fallback
    if not private_html:
        private_html = doc.get("entityHolderMap", {}).get("nl-NL", {}).get("privateAnswer")
    
    if not public_html:
        public_html = doc.get("entityHolderMap", {}).get("nl-NL", {}).get("publicAnswer")
    
    rec = {
        "source_file": filename,
        "id": get_id(doc),
        "title": title,
        "private_answer_html": private_html,
        "private_answer_text": strip_html(private_html),
        "publicAnswer_html": public_html,
        "publicAnswer_text": strip_html(public_html),
        "links_in_private_answer": extract_content_links(private_html or ""),
        "topic_tags": get_tags(doc, "topic"),
        "agentskill_tags": get_tags(doc, "agentskill"),
        "knowledgebase_tags": get_tags(doc, "knowledgeBase"),
        "must_read": bool(find_field(fvals, "mustRead::::") == "true"),
        'full_text': "Public Answer: " + strip_html(public_html) + ' Private Answer: ' + strip_html(private_html)
    }
    
    return rec


def get_duplicates_details(extracted_df: pd.DataFrame) -> pd.DataFrame:
    """Get details of duplicate entries in the extracted DataFrame.

    :param extracted_df: DataFrame with extracted content.
    :return: DataFrame with details of duplicate entries.
    """
    title_counts = extracted_df.groupby("title").size().reset_index(name="count")
    dupes = title_counts[title_counts["count"] > 1]
    dupe_details = (
        extracted_df[extracted_df["title"].isin(dupes["title"])]
        .groupby("title")[["id", "source_file"]]
        .agg(list)
        .reset_index()
    )
    return dupe_details