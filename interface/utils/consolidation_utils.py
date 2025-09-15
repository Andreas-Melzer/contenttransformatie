
import json

def json_to_markdown(data: dict) -> str:
    """Converts the consolidated JSON data to a Markdown formatted string.

    :param data: dict, The dictionary loaded from the JSON output.
    :return: str, A string containing the formatted Markdown text.
    """
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
        publiek = item.get('publieke_informatie', {}).get('fragmenten', [])
        if publiek:
            markdown_parts.append("### Publieke Informatie")
            for fragment in publiek:
                markdown_parts.append(f"- **[{fragment.get('bron_km', 'ONBEKEND')}]**: {fragment.get('tekst_fragment', '')}")
            markdown_parts.append("") # Add a blank line for spacing

        # Interne Instructies
        intern = item.get('interne_informatie', {}).get('fragmenten', [])
        if intern:
            markdown_parts.append("### Interne Instructies")
            for fragment in intern:
                markdown_parts.append(f"- **[{fragment.get('bron_km', 'ONBEKEND')}]**: {fragment.get('tekst_fragment', '')}")
            markdown_parts.append("")

    # --- Subvragen ---
    subvragen = data.get('subvragen_consolidatie', [])
    if subvragen:
        markdown_parts.append("## Consolidatie voor Subvragen")
        for item in subvragen:
            markdown_parts.append(f"### Subvraag: {item.get('vraag', '')}")
            
            # Publieke Informatie Subvraag
            publiek_sub = item.get('publieke_informatie', {}).get('fragmenten', [])
            if publiek_sub:
                markdown_parts.append("#### Publieke Informatie")
                for fragment in publiek_sub:
                    markdown_parts.append(f"- **[{fragment.get('bron_km', 'ONBEKEND')}]**: {fragment.get('tekst_fragment', '')}")
                markdown_parts.append("")

            # Interne Instructies Subvraag
            intern_sub = item.get('interne_informatie', {}).get('fragmenten', [])
            if intern_sub:
                markdown_parts.append("#### Interne Instructies")
                for fragment in intern_sub:
                    markdown_parts.append(f"- **[{fragment.get('bron_km', 'ONBEKEND')}]**: {fragment.get('tekst_fragment', '')}")
                markdown_parts.append("")
        
    # --- Conflicten ---
    conflicten = data.get('gedetecteerde_conflicten', [])
    if conflicten:
        markdown_parts.append("---")
        markdown_parts.append("## ❗ Gedetecteerde Conflicten")
        for conflict in conflicten:
            bronnen = ", ".join(conflict.get('bron_kms', []))
            markdown_parts.append(f"- **Conflict**: {conflict.get('conflict_beschrijving', '')} (Bronnen: {bronnen})")
        markdown_parts.append("")

    # --- Hiaten ---
    hiaten = data.get('informatie_hiaten', [])
    if hiaten:
        markdown_parts.append("---")
        markdown_parts.append("## ❓ Informatiehiaten")
        for hiaat in hiaten:
            markdown_parts.append(f"- **Hiaat**: {hiaat.get('hiaat_beschrijving', '')} (Relevant voor: {hiaat.get('relevante_vraag', '')})")
        markdown_parts.append("")

    return "\n".join(markdown_parts)
