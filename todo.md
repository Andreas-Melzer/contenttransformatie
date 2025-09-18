(2025-09-14) #TODO uitwerken consolidatie pagina -> toevoegen geconsolideert document aan project
    (2025-09-15) #TODO De output van de consolidatie agent wordt nu op een lelijke manier gescheiden van het bericht aan de gebruikter dit moet met tools worden opgelost.
(2025-09-14) #TODO uitwerken herschrijven pagina

#TODO updaten van zoek index er worden nu te weinig documenten gevonden.
#TODO debugging van agent in interface
#TODO agent aanpassen zodat deze beter tools gebruikt

# Consolidatie Interface
#TODO Volledige implementatie van de consolidatie interface
    #TODO Toevoegen van geconsolideerd document aan project
    #TODO Verbeteren van de manier waarop de output van de consolidatie agent wordt gescheiden van het bericht aan de gebruiker (moet met tools worden opgelost)
    #TODO Automatische consolidatie functionaliteit verbeteren
    #TODO UI/UX verbeteringen voor de consolidatie pagina

# Herschrijven Interface
[-] Eerste implementatie van de herschrijf interface
    [x] Basisfunctionaliteit voor herschrijven van geconsolideerde content
    [x] Integratie met LLM-agent voor herschrijven
    [x] UI/UX design voor de herschrijf pagina
    #TODO Opslaan van herschreven content in project

# Unit Tests
[-] Aanmaken van een test directory structuur
    [x] Aanmaken van tests directory met __init__.py
    [x] Aanmaken van conftest.py voor pytest configuratie
    [x] Aanmaken van requirements-dev.txt voor test afhankelijkheden
    [x] Eerste unit tests voor Project klasse
    [x] Eerste unit tests voor utility functies
    #TODO Unit tests voor de interface componenten
    #TODO Unit tests voor de LLM client functionaliteit
    #TODO Integratietests voor de agent functionaliteit

# Architectuur Verbeteringen
#TODO Refactoring van de codebase voor betere scheiding van verantwoordelijkheden
    #TODO Implementatie van een service-laag tussen interface en business logica
    #TODO Verbeteren van de project data persistence strategie
    #TODO Centraliseren van configuratiebeheer
    #TODO Implementatie van dependency injection voor betere testbaarheid
    #TODO Verbeteren van de error handling en logging
    #TODO Optimalisatie van de document loading en caching mechanismen
    #TODO Verbeteren van de agent tool gebruikt (betere tool selection en execution)
