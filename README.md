# Content Creatie Applicatie

Een Streamlit-gebaseerde applicatie voor het creëren van content door het combineren van informatie uit meerdere documenten.

## Overzicht

Deze applicatie is ontworpen om gebruikers te helpen bij het creëren van content door relevante informatie te extraheren uit een verzameling documenten en deze te consolideren in een gestructureerd formaat. Het is speciaal ontwikkeld voor gebruik binnen de Belastingdienst.

## Functies

- **Projectbeheer**: Maak en beheer meerdere content-projecten
- **Document Zoeken**: Zoek door een grote verzameling documenten om relevante informatie te vinden
- **Document Selectie**: Selecteer specifieke documenten voor elk project
- **Consolidatie**: Combineer informatie uit meerdere geselecteerde documenten
- **Herschrijven**: Herschrijf de geconsolideerde content in een gestructureerd formaat
- **Gebruiksvriendelijke Interface**: Intuïtieve Streamlit-gebaseerde gebruikersinterface

## Vereisten

- Python 3.8+
- De benodigde pakketten staan in [`requirements.txt`](requirements.txt:1)

## Installatie

1. Clone deze repository:
   ```bash
   git clone <repository-url>
   cd contentcreatie
   ```

2. Installeer de vereiste pakketten:
   ```bash
   pip install -r requirements.txt
   ```

3. Voor ontwikkeling, installeer ook de ontwikkelafhankelijkheden:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Gebruik

Start de applicatie met het volgende commando:

```bash
python run_interface.py
```

De applicatie opent automatisch in je standaardwebbrowser.

## Projectstructuur

- [`interface/`](interface/:1) - Streamlit-gebaseerde gebruikersinterface
- [`llm_client/`](llm_client/:1) - LLM-functionaliteit en tools
- [`data/`](data/:1) - Documenten en projectgegevens
- [`prompt_templates/`](prompt_templates/:1) - Sjablonen voor LLM-prompts
- [`utils/`](utils/:1) - Hulpprogramma's en hulpfuncties
- [`implementations/`](implementations/:1) - Implementaties van tools en andere componenten
- [`config/`](config/:1) - Configuratiebestanden
- [`pipelines/`](pipelines/:1) - Data processing pipelines
- [`tests/`](tests/:1) - Unit tests en integratietests

## Ontwikkeling

### TODOs

Zie [`todo.md`](todo.md:1) voor een uitgebreide lijst met openstaande taken en verbeterpunten. Deze omvat:

- Volledige implementatie van de consolidatie interface
- Eerste implementatie van de herschrijf interface
- Unit test ontwikkeling
- Architectuur verbeteringen

### Ontwikkelingsstappen

1. **Consolidatie Interface**:
   - Voltooi de implementatie van de consolidatie functionaliteit
   - Verbeter de manier waarop de output van de consolidatie agent wordt verwerkt
   - Voeg functionaliteit toe om geconsolideerde documenten aan projecten toe te voegen

2. **Herschrijf Interface**:
   - Ontwikkel de basisfunctionaliteit voor het herschrijven van geconsolideerde content
   - Integreer LLM-agent functionaliteit voor herschrijven
   - Ontwerp en implementeer de gebruikersinterface voor herschrijven

3. **Testen**:
   - Stel een test directory structuur op
   - Schrijf unit tests voor de belangrijkste componenten
   - Voeg integratietests toe voor agent functionaliteit

4. **Architectuur Verbeteringen**:
   - Refactor de codebase voor betere scheiding van verantwoordelijkheden
   - Implementeer een service-laag tussen interface en business logica
   - Verbeter de project data persistence strategie
   - Centraliseer configuratiebeheer

### Testen

Deze applicatie bevat unit tests die kunnen worden uitgevoerd met pytest:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_project.py
```

## Bijdragen

Bijdragen aan dit project zijn welkom. Gelieve een fork te maken van de repository en een pull request in te dienen met je wijzigingen.

## Licentie

Dit project is bedoeld voor intern gebruik binnen de Belastingdienst.