import json

def enrich_fragments_with_metadata(fragments, doc_store):
    """
    Iterates through a list of fragments, finds the corresponding document in the
    doc_store, and adds metadata fields to each fragment.

    :param fragments: list, A list of fragment dictionaries.
    :param doc_store: dict, The document store containing document objects.
    """
    if not fragments:
        return

    for fragment in fragments:
        km_number = fragment.get("bron_km")
        if not km_number:
            continue

        # Get the document from the document store using the km number
        doc = doc_store.documents.get(km_number)

        if doc:
            # Add metadata fields to the fragment dictionary
            fragment["VRAAG"] = doc.metadata.get("VRAAG", "")
            fragment["BELASTINGSOORT"] = doc.metadata.get("BELASTINGSOORT", "")
            fragment["PROCES_ONDERWERP"] = doc.metadata.get("PROCES_ONDERWERP", "")
            fragment["PRODUCT_SUBONDERWERP"] = doc.metadata.get("PRODUCT_SUBONDERWERP", "")
        else:
            # Handle cases where the km_number is not in the doc_store
            print(f"Warning: KM number '{km_number}' not found in doc_store.")


def enrich_consolidation(data, doc_store):
    """
    Main function to process the entire JSON object, enriching all fragments.

    :param data: dict, The full JSON data object.
    :param doc_store: dict, The document store.
    :return: dict, The modified JSON data object with enriched fragments.
    """
    # Process fragments for the main question ("hoofdvraag")
    for item in data.get("consolidatie", []):
        for info_type in ["publieke_informatie", "interne_informatie"]:
            if info_type in item:
                enrich_fragments_with_metadata(item[info_type].get("fragmenten"), doc_store)

    # Process fragments for all sub-questions ("subvragen")
    for sub_vraag in data.get("subvragen_consolidatie", []):
        for info_type in ["publieke_informatie", "interne_informatie"]:
            if info_type in sub_vraag:
                enrich_fragments_with_metadata(sub_vraag[info_type].get("fragmenten"), doc_store)

    return data