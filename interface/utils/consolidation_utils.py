
import json

def _format_fragment(fragment: dict) -> str:
    """Format a text fragment with its source information.
    
    :param fragment: dict, The fragment dictionary containing 'tekst_fragment' and 'bron_km'
    :return: str, Formatted string for the fragment
    """
    bron_km = fragment.get('bron_km', 'ONBEKEND')
    # Handle case where bron_km might be a string instead of a list
    if isinstance(bron_km, str):
        bron_km = [bron_km]
    bronnen = ",".join([km for km in bron_km])
    return f"* {fragment.get('tekst_fragment', '')} **BRON: {bronnen}** \n"


def _add_section_content(markdown_parts: list, section_data: dict, section_title: str) -> None:
    """Add content for a section (publieke_informatie or interne_informatie) to markdown parts.
    
    :param markdown_parts: list, The list of markdown parts to append to
    :param section_data: dict, The section data containing 'fragmenten'
    :param section_title: str, The title for this section
    """
    fragmenten = section_data.get('fragmenten', [])
    if fragmenten:
        markdown_parts.append(f"### {section_title}")
        for fragment in fragmenten:
            markdown_parts.append(_format_fragment(fragment))
        markdown_parts.append("")


def format_consolidated_json(data: dict) -> str:
    """Converts the consolidated JSON data to a Markdown formatted string.

    :param data: dict, The dictionary loaded from the JSON output.
    :return: str, A string containing the formatted Markdown text.
    """
    # Handle None or empty data
    if not data:
        return ""
    
    markdown_parts = []
    if "hoofdvraag" not in data:
        return "Invalid json format"
    
    # --- Hoofdvraag ---
    markdown_parts.append(f"# {data.get('hoofdvraag', 'Geen Hoofdvraag')}")
    markdown_parts.append("---")

    # --- Consolidatie Hoofdvraag ---
    for item in data.get('consolidatie', []):
        markdown_parts.append(f"## Consolidatie voor: {item.get('vraag', '')}")
        
        # Publieke Informatie
        publiek = item.get('publieke_informatie', {})
        _add_section_content(markdown_parts, publiek, "Openbare Informatie")

        # Interne Instructies
        intern = item.get('interne_informatie', {})
        _add_section_content(markdown_parts, intern, "Interne Informatie")

    # --- Subvragen ---
    subvragen = data.get('subvragen_consolidatie', [])
    if subvragen:
        markdown_parts.append("## Consolidatie voor Subvragen")
        for item in subvragen:
            markdown_parts.append(f"### Subvraag: {item.get('vraag', '')}")
            
            # Publieke Informatie Subvraag
            publiek_sub = item.get('publieke_informatie', {})
            _add_section_content(markdown_parts, publiek_sub, "Publieke Informatie")

            # Interne Instructies Subvraag
            intern_sub = item.get('interne_informatie', {})
            _add_section_content(markdown_parts, intern_sub, "Interne Instructies")
        
    conflicten = data.get('gedetecteerde_conflicten', [])
    if conflicten:
        markdown_parts.append("---")
        markdown_parts.append("##Gedetecteerde Conflicten")
        for conflict in conflicten:
            bronnen = ", ".join(conflict.get('bron_kms', []))
            markdown_parts.append(f"- **Conflict**: {conflict.get('conflict_beschrijving', '')} (Bronnen: {bronnen})")
        markdown_parts.append("")

    hiaten = data.get('informatie_hiaten', [])
    if hiaten:
        markdown_parts.append("---")
        markdown_parts.append("##Informatiehiaten")
        for hiaat in hiaten:
            markdown_parts.append(f"- **Hiaat**: {hiaat.get('hiaat_beschrijving', '')} (Relevant voor: {hiaat.get('relevante_vraag', '')})")
        markdown_parts.append("")

    return "\n".join(markdown_parts)
