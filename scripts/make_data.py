"""Generate the synthetic data set behind the SkillDraft case.

    python3 scripts/make_data.py           # write data/
    python3 scripts/make_data.py --check   # CI: fail if data/ is not what this script produces

What it writes
- data/taxonomy.json            71 skills, bilingual aliases and definitions (what the product ships)
- data/job_descriptions.jsonl   300 job descriptions (EN and NL) with gold skills, importance,
                                evidence spans, distractors and coded-language flags
- data/counterfactuals.jsonl    4 variants per dev and test description (he/she, name, age wording)
- data/people.jsonl             60 employee skill profiles for the internal-mobility match
- data/cvs.jsonl                160 fictional CVs (EN and NL) with gold skills, distractors ("I would
                                like to learn X", "no experience with X yet") and personal-data spans
- data/cv_counterfactuals.jsonl 2 variants per dev and test CV (other name, birth year 30 years apart)

Why it is built this way
- Gold labels come from the generator, not from the pipeline. The generator decides which skill
  a sentence expresses and records it, so the evals compare the pipeline against an oracle it
  did not write.
- Paraphrases (implicit mentions such as "you keep our workloads scaled across clusters") live
  only in this file. The taxonomy that the product ships does not contain them, so the matcher
  cannot find them by string lookup.
- Every rendered sentence is checked with an independent alias scan: a sentence may only
  contain the aliases the generator meant to put there. That keeps the gold labels honest.
- Hard cases are on purpose: ambiguous aliases (SAP, lean, safety, containers, transformers),
  skills mentioned in "about us" or "what we offer", negated requirements, descriptions
  without headings, two skills in one sentence, Dutch and English.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEED = 20261021
TAXONOMY_VERSION = "2026.10"

# ------------------------------------------------------------------ taxonomy
# (id, label, family, aliases_en, aliases_nl, definition_en, definition_nl, paraphrases_en, paraphrases_nl)
# Aliases are "|"-separated; a leading "~" marks an alias that is ambiguous out of context.
# Paraphrases are generator-only: they are never written to taxonomy.json.
SKILLS = [
    # software
    ("python", "Python", "software", "Python|Python 3", "", "General-purpose programming language used for scripting, back-end services, automation and data work.", "Programmeertaal voor scripts, back-end diensten, automatisering en datawerk.", [], []),
    ("java", "Java", "software", "Java|Java EE|Spring Boot", "", "Object-oriented programming language for enterprise back-end applications on the JVM.", "Objectgeoriënteerde programmeertaal voor zakelijke back-end toepassingen op de JVM.", ["You build enterprise back-end applications that run on the JVM."], ["Je bouwt zakelijke back-end toepassingen die op de JVM draaien."]),
    ("javascript", "JavaScript / TypeScript", "software", "JavaScript|TypeScript|Node.js|React", "", "Languages and frameworks for interactive web front-ends and Node.js services.", "Talen en frameworks voor interactieve webinterfaces en Node.js-diensten.", ["You create interactive web front-ends that run in the browser."], ["Je maakt interactieve webinterfaces die in de browser draaien."]),
    ("sql", "SQL", "software", "SQL|PostgreSQL|MySQL|SQL Server", "", "Querying, joining and managing data in relational databases.", "Data opvragen, koppelen en beheren in relationele databanken.", ["You write queries that join and aggregate tables in our relational data stores."], ["Je schrijft queries die tabellen in onze relationele databanken koppelen en samenvatten."]),
    ("rest-api-design", "REST API design", "software", "REST API|REST APIs|RESTful|API design|OpenAPI", "API-ontwerp", "Designing HTTP interfaces between systems: resources, versioning, error handling and contracts.", "HTTP-interfaces tussen systemen ontwerpen: resources, versies, foutafhandeling en contracten.", ["You define the HTTP interfaces through which our systems exchange data."], ["Je ontwerpt de HTTP-interfaces waarlangs onze systemen gegevens uitwisselen."]),
    ("docker", "Containerisation (Docker)", "software", "Docker|containerisation|containerization|~containers", "containerisatie", "Packaging applications and their dependencies into portable container images.", "Toepassingen en hun afhankelijkheden verpakken in draagbare container-images.", ["You package our services into portable images with all their dependencies."], ["Je verpakt onze diensten in draagbare images met al hun afhankelijkheden."]),
    ("kubernetes", "Kubernetes", "software", "Kubernetes|K8s|OpenShift", "", "Orchestrating containerised workloads across clusters: deployment, scaling and self-healing.", "Workloads in containers orkestreren over clusters: uitrollen, schalen en zelfherstel.", ["You keep our workloads deployed, scaled and healthy across several clusters."], ["Je houdt onze workloads draaiend en geschaald over meerdere clusters."]),
    ("ci-cd", "CI/CD pipelines", "software", "CI/CD|continuous integration|continuous delivery|GitHub Actions|GitLab CI|Jenkins", "", "Automating the build, test and release of software through pipelines.", "Het bouwen, testen en uitrollen van software automatiseren met pipelines.", ["You automate how our code is built, tested and released to production."], ["Je automatiseert hoe onze code gebouwd, getest en naar productie uitgerold wordt."]),
    ("aws", "Amazon Web Services (AWS)", "software", "AWS|Amazon Web Services", "", "Building and running workloads on Amazon's public cloud.", "Workloads bouwen en draaien in de publieke cloud van Amazon.", ["You run our workloads on Amazon's public cloud and keep cloud costs in check."], ["Je draait onze workloads in de publieke cloud van Amazon en houdt de cloudkosten onder controle."]),
    ("automated-testing", "Automated testing", "software", "automated testing|unit testing|unit tests|test automation|pytest|integration tests", "testautomatisering|geautomatiseerd testen", "Writing automated unit, integration and end-to-end tests that guard software quality.", "Geautomatiseerde unit-, integratie- en end-to-end tests schrijven die de softwarekwaliteit bewaken.", ["You make sure every change is covered by checks that run without manual effort."], ["Je zorgt dat elke wijziging gecontroleerd wordt door checks die zonder handwerk draaien."]),
    ("git", "Git", "software", "Git|version control", "versiebeheer", "Tracking changes to code with branches, commits and merges.", "Wijzigingen aan code bijhouden met branches, commits en merges.", ["You keep the code history clean with short-lived branches and reviewed merges."], ["Je houdt de codegeschiedenis netjes met kortlevende branches en nagekeken merges."]),
    # data
    ("data-analysis", "Data analysis", "data", "data analysis|data analytics", "data-analyse|analyse van data", "Exploring and interpreting data to answer business questions.", "Data verkennen en interpreteren om zakelijke vragen te beantwoorden.", ["You turn raw operational figures into insights that managers act on."], ["Je zet ruwe operationele cijfers om in inzichten waarop managers beslissen."]),
    ("dashboarding", "Dashboarding (Power BI)", "data", "Power BI|PowerBI|Tableau|DAX|~dashboards", "", "Building interactive reports and dashboards that track KPIs.", "Interactieve rapporten en dashboards bouwen die KPI's opvolgen.", ["You build interactive reports that show managers their KPIs at a glance."], ["Je bouwt interactieve rapporten die managers hun KPI's in één oogopslag tonen."]),
    ("statistics", "Statistics", "data", "statistics|statistical analysis|regression analysis|hypothesis testing", "statistiek|statistische analyse", "Applying statistical methods such as significance tests and regression to data.", "Statistische methoden zoals significantietests en regressie toepassen op data.", ["You know when a difference between two groups is significant and when it is noise."], ["Je weet wanneer een verschil tussen twee groepen significant is en wanneer het ruis is."]),
    ("machine-learning", "Machine learning", "data", "machine learning|predictive modelling|predictive modeling|scikit-learn", "", "Training and evaluating models that learn patterns from data to make predictions.", "Modellen trainen en evalueren die patronen uit data leren om voorspellingen te doen.", ["You train models that predict outcomes from historical data and monitor their accuracy."], ["Je traint modellen die uitkomsten voorspellen op basis van historische data en je bewaakt hun nauwkeurigheid."]),
    ("data-modelling", "Data modelling", "data", "data modelling|data modeling|dimensional modelling|star schema", "datamodellering", "Designing tables, keys and relationships for analytical and operational data.", "Tabellen, sleutels en relaties ontwerpen voor analytische en operationele data.", ["You design the tables and relationships that our reporting layer is built on."], ["Je ontwerpt de tabellen en relaties waarop onze rapportering steunt."]),
    ("data-pipelines", "Data pipelines (ETL)", "data", "ETL|ELT|data pipelines|Airflow|dbt", "datapijplijnen", "Moving and transforming data from source systems into a warehouse on a schedule.", "Data volgens planning van bronsystemen naar een datawarehouse brengen en transformeren.", ["You move data reliably from source systems into the warehouse every night."], ["Je brengt data elke nacht betrouwbaar van de bronsystemen naar het datawarehouse."]),
    ("deep-learning", "Deep learning (PyTorch)", "data", "PyTorch|deep learning|TensorFlow|neural networks", "neurale netwerken", "Building and training neural networks with frameworks such as PyTorch.", "Neurale netwerken bouwen en trainen met frameworks zoals PyTorch.", ["You train large models on GPUs and tune their layers and loss functions."], ["Je traint grote modellen op GPU's en stemt hun lagen en verliesfuncties af."]),
    ("nlp", "Natural language processing", "data", "NLP|natural language processing|text mining|large language models|LLMs|~transformers", "", "Building systems that understand, classify or generate human language.", "Systemen bouwen die menselijke taal begrijpen, classificeren of genereren.", ["You build systems that read and classify free text such as emails and job descriptions."], ["Je bouwt systemen die vrije tekst zoals e-mails en vacatures lezen en classificeren."]),
    # maintenance
    ("plc-programming", "PLC programming", "maintenance", "PLC|PLC programming|Siemens S7|TIA Portal", "PLC-programmatie", "Programming and modifying programmable logic controllers that drive machines.", "Programmeerbare sturingen (PLC's) programmeren en aanpassen die machines aansturen.", ["You program and adjust the controllers that drive our production lines."], ["Je programmeert en past de sturingen aan die onze productielijnen aandrijven."]),
    ("preventive-maintenance", "Preventive maintenance", "maintenance", "preventive maintenance|planned maintenance|TPM", "preventief onderhoud", "Planning inspections and part replacements so equipment does not fail.", "Inspecties en vervangingen plannen zodat installaties niet uitvallen.", ["You plan inspections and part replacements before machines break down."], ["Je plant inspecties en vervangingen van onderdelen voordat machines stilvallen."]),
    ("electrical-troubleshooting", "Electrical troubleshooting", "maintenance", "electrical troubleshooting|electrical diagnostics|BA4|BA5", "elektrische storingen|elektrische diagnose", "Diagnosing faults in wiring, motors, drives and control cabinets.", "Fouten opsporen in bekabeling, motoren, aandrijvingen en schakelkasten.", ["You find the cause of faults in wiring, motors and control cabinets."], ["Je zoekt de oorzaak van fouten in bekabeling, motoren en schakelkasten."]),
    ("hydraulics-pneumatics", "Hydraulics and pneumatics", "maintenance", "hydraulics|pneumatics|hydraulic systems", "hydrauliek|pneumatiek", "Maintaining hydraulic and compressed-air systems: cylinders, valves and pumps.", "Hydraulische en persluchtsystemen onderhouden: cilinders, ventielen en pompen.", ["You repair cylinders, valves and compressed-air circuits on our machines."], ["Je herstelt cilinders, ventielen en persluchtcircuits op onze machines."]),
    ("welding", "Welding", "maintenance", "welding|TIG welding|MIG welding|MIG/MAG", "lassen", "Joining metal parts with arc welding processes such as TIG and MIG/MAG.", "Metalen onderdelen verbinden met booglasprocessen zoals TIG en MIG/MAG.", ["You join steel parts with an arc and inspect the seams."], ["Je verbindt stalen onderdelen met een lasboog en controleert de naden."]),
    ("cnc-machining", "CNC machining", "maintenance", "CNC|CNC machining", "CNC-bewerking", "Setting up and operating computer-controlled milling and turning machines.", "Computergestuurde frees- en draaimachines instellen en bedienen.", ["You set up and run computer-controlled milling and turning machines."], ["Je stelt computergestuurde frees- en draaibanken in en bedient ze."]),
    ("technical-drawings", "Reading technical drawings", "maintenance", "technical drawings|blueprints|electrical schematics", "technische tekeningen|elektrische schema's", "Reading plans, schematics and drawings to understand how equipment is built.", "Plannen, schema's en tekeningen lezen om te begrijpen hoe installaties opgebouwd zijn.", ["You read plans to understand how an installation is put together."], ["Je leest plannen om te begrijpen hoe een installatie opgebouwd is."]),
    ("root-cause-analysis", "Root-cause analysis", "maintenance", "root cause analysis|root-cause analysis|5 why|Ishikawa|8D", "oorzaakanalyse", "Finding the underlying cause of recurring problems with structured methods.", "De onderliggende oorzaak van terugkerende problemen vinden met gestructureerde methoden.", ["You dig past the symptoms of a recurring breakdown until you find what really causes it."], ["Je zoekt bij terugkerende storingen verder dan de symptomen tot je de echte oorzaak vindt."]),
    # production
    ("lean-manufacturing", "Lean manufacturing", "production", "~lean|lean manufacturing|kaizen|5S|continuous improvement|Six Sigma", "continu verbeteren", "Removing waste from production processes with methods such as kaizen and 5S.", "Verspilling uit productieprocessen halen met methoden zoals kaizen en 5S.", ["You remove waste from our processes and run improvement workshops on the shop floor."], ["Je haalt verspilling uit onze processen en leidt verbeterworkshops op de werkvloer."]),
    ("quality-control", "Quality control", "production", "quality control|quality inspection|SPC", "kwaliteitscontrole", "Inspecting products against specifications and blocking what does not conform.", "Producten tegen specificaties controleren en blokkeren wat niet conform is.", ["You check samples from every batch against the specifications and block what fails."], ["Je controleert stalen van elke batch tegen de specificaties en blokkeert wat afwijkt."]),
    ("iso-9001", "ISO 9001", "production", "ISO 9001|ISO9001|quality management system", "kwaliteitsmanagementsysteem", "Running a certified quality management system and preparing for audits.", "Een gecertificeerd kwaliteitsmanagementsysteem beheren en audits voorbereiden.", ["You keep our certified quality system audit-ready and handle the yearly audit."], ["Je houdt ons gecertificeerde kwaliteitssysteem auditklaar en begeleidt de jaarlijkse audit."]),
    ("food-safety", "Food safety (HACCP)", "production", "HACCP|food safety|BRCGS", "voedselveiligheid", "Controlling hygiene and critical control points in food production.", "Hygiëne en kritische controlepunten in de voedingsproductie bewaken.", ["You make sure hygiene and critical control points are respected on the food lines."], ["Je bewaakt de hygiëne en de kritische controlepunten op de voedingslijnen."]),
    ("production-planning", "Production planning", "production", "production planning|capacity planning|MRP", "productieplanning|capaciteitsplanning", "Scheduling orders on lines and machines so that capacity and deadlines match.", "Orders op lijnen en machines inplannen zodat capaciteit en deadlines kloppen.", ["You decide which orders run on which line and when, so deadlines are met."], ["Je beslist welke orders wanneer op welke lijn lopen, zodat deadlines gehaald worden."]),
    ("shift-leadership", "Shift leadership", "production", "shift leadership|shift leader|~team leader", "ploegleider|ploegleiding", "Leading a team of operators during a shift and handing over to the next one.", "Een ploeg operatoren aansturen tijdens een shift en overdragen aan de volgende.", ["You lead the operators on your shift and hand over cleanly to the next team."], ["Je stuurt de operatoren van jouw ploeg aan en draagt netjes over aan de volgende ploeg."]),
    ("workplace-safety", "Workplace safety", "production", "workplace safety|health and safety|VCA|~safety", "veiligheid op het werk|~veiligheid", "Preventing accidents: risk analysis, safe work instructions and incident follow-up.", "Ongevallen voorkomen: risicoanalyse, veilige werkinstructies en opvolging van incidenten.", ["You spot unsafe situations on the floor and make sure incidents are reported and fixed."], ["Je ziet onveilige situaties op de vloer en zorgt dat incidenten gemeld en opgelost worden."]),
    ("forklift", "Forklift operation", "production", "forklift|reach truck|forklift licence", "heftruck|reachtruck|heftruckattest", "Operating forklifts and reach trucks to move goods in a warehouse or plant.", "Heftrucks en reachtrucks besturen om goederen te verplaatsen in een magazijn of fabriek.", ["You move pallets safely between the racks and the loading docks."], ["Je verplaatst paletten veilig tussen de rekken en de laadkades."]),
    # logistics
    ("wms", "Warehouse management systems", "logistics", "WMS|warehouse management system|warehouse management systems", "magazijnbeheersysteem", "Configuring and using software that tracks stock locations and warehouse tasks.", "Software configureren en gebruiken die voorraadlocaties en magazijntaken opvolgt.", ["You configure the software that tells pickers where every pallet is stored."], ["Je configureert de software die orderpickers vertelt waar elke pallet ligt."]),
    ("sap-logistics", "SAP (logistics modules)", "logistics", "~SAP|SAP MM|SAP WM|S/4HANA", "", "Working with the materials management and warehouse modules of SAP.", "Werken met de modules voor materiaalbeheer en magazijn van SAP.", ["You maintain material masters and purchase orders in the logistics modules of our ERP."], ["Je beheert materiaalfiches en bestelbonnen in de logistieke modules van ons ERP."]),
    ("inventory-management", "Inventory management", "logistics", "inventory management|stock control|cycle counting", "voorraadbeheer", "Keeping stock levels and stock records accurate.", "Voorraadniveaus en voorraadgegevens juist houden.", ["You keep stock levels right so we never run out and never overstock."], ["Je houdt de voorraadniveaus juist zodat we nooit tekortkomen en nooit te veel hebben."]),
    ("procurement", "Procurement", "logistics", "procurement|purchasing|sourcing", "aankoop|inkoop", "Selecting suppliers, comparing quotes and contracting goods and services.", "Leveranciers selecteren, offertes vergelijken en goederen en diensten contracteren.", ["You select suppliers, compare quotes and agree contracts for raw materials."], ["Je selecteert leveranciers, vergelijkt offertes en sluit contracten af voor grondstoffen."]),
    ("supply-chain-planning", "Supply chain planning", "logistics", "supply chain planning|demand planning|sales and operations planning|~supply chain", "vraagplanning", "Forecasting demand and aligning it with supply, production and stock.", "De vraag voorspellen en afstemmen op aanvoer, productie en voorraad.", ["You forecast demand and align it with what our plants and suppliers can deliver."], ["Je voorspelt de vraag en stemt die af op wat onze fabrieken en leveranciers kunnen leveren."]),
    ("customs", "Customs documentation", "logistics", "customs documentation|customs|Incoterms", "douane|douanedocumenten", "Preparing import and export declarations and applying trade terms.", "Invoer- en uitvoeraangiften opmaken en handelsvoorwaarden toepassen.", ["You prepare the paperwork that lets our shipments cross EU borders without delays."], ["Je maakt de papieren klaar waarmee onze zendingen zonder vertraging de EU-grens over kunnen."]),
    ("route-planning", "Transport and route planning", "logistics", "route planning|transport planning|TMS", "routeplanning|transportplanning", "Planning trucks, routes and delivery sequences.", "Vrachtwagens, routes en de volgorde van leveringen plannen.", ["You decide which truck takes which deliveries and in what order."], ["Je beslist welke vrachtwagen welke leveringen in welke volgorde rijdt."]),
    # sales
    ("b2b-sales", "B2B sales", "sales", "B2B sales|business development|new business|prospecting", "prospectie", "Finding and winning new business customers.", "Nieuwe zakelijke klanten vinden en binnenhalen.", ["You find new industrial customers and turn first meetings into signed deals."], ["Je vindt nieuwe industriële klanten en zet eerste gesprekken om in getekende deals."]),
    ("negotiation", "Negotiation", "sales", "negotiation|negotiating", "onderhandelen|onderhandelingsvaardigheden", "Reaching agreements on price and terms while protecting the relationship.", "Akkoorden bereiken over prijs en voorwaarden zonder de relatie te schaden.", ["You hold your ground on price and terms while keeping the relationship good."], ["Je houdt voet bij stuk over prijs en voorwaarden en houdt de relatie goed."]),
    ("crm", "CRM (Salesforce)", "sales", "CRM|Salesforce|HubSpot", "", "Keeping customer contacts, opportunities and activities up to date in a CRM.", "Klantcontacten, opportuniteiten en activiteiten bijhouden in een CRM.", ["You keep every customer contact and opportunity up to date in our sales system."], ["Je houdt elk klantcontact en elke opportuniteit up-to-date in ons verkoopsysteem."]),
    ("account-management", "Key account management", "sales", "account management|key account management|key accounts", "accountbeheer", "Managing and growing long-term relationships with important customers.", "Langdurige relaties met belangrijke klanten beheren en laten groeien.", ["You are the long-term point of contact for our largest customers and grow their business."], ["Je bent het vaste aanspreekpunt van onze grootste klanten en laat hun omzet groeien."]),
    ("customer-service", "Customer service", "sales", "customer service|customer support", "klantendienst|klantenservice", "Answering customer questions and solving their problems by phone, email or chat.", "Vragen van klanten beantwoorden en hun problemen oplossen via telefoon, e-mail of chat.", ["You answer customer questions by phone and email and solve their problems quickly."], ["Je beantwoordt vragen van klanten via telefoon en e-mail en lost hun problemen snel op."]),
    ("market-analysis", "Market analysis", "sales", "market analysis|market research|competitor analysis", "marktanalyse|marktonderzoek", "Studying competitors, prices and trends to inform commercial decisions.", "Concurrenten, prijzen en trends bestuderen om commerciële beslissingen te onderbouwen.", ["You track competitors and price trends and tell us where the market is heading."], ["Je volgt concurrenten en prijstrends op en vertelt ons waar de markt naartoe gaat."]),
    ("presentation-skills", "Presentation skills", "sales", "presentation skills|presenting|public speaking", "presenteren|presentatievaardigheden", "Explaining ideas and products clearly to an audience.", "Ideeën en producten helder uitleggen aan een publiek.", ["You explain our products clearly in front of a room of buyers."], ["Je legt onze producten helder uit voor een zaal vol aankopers."]),
    # hr
    ("recruitment", "Recruitment", "hr", "recruitment|recruiting|talent acquisition", "rekrutering|werving", "Finding, interviewing and hiring candidates.", "Kandidaten zoeken, interviewen en aanwerven.", ["You find, interview and hire the people our plants need."], ["Je zoekt, interviewt en werft de mensen die onze fabrieken nodig hebben."]),
    ("labour-law", "Belgian labour law", "hr", "labour law|labor law|employment law", "arbeidsrecht|sociaal recht|sociale wetgeving", "Applying employment contracts, dismissal rules and working-time law in Belgium.", "Arbeidscontracten, ontslagregels en arbeidstijdwetgeving in België toepassen.", ["You advise managers on contracts, dismissals and working-time rules under Belgian law."], ["Je adviseert managers over contracten, ontslagen en arbeidstijdregels volgens de Belgische wet."]),
    ("payroll", "Payroll", "hr", "payroll|payroll administration|salary administration", "loonadministratie|personeelsadministratie", "Calculating and paying salaries correctly, including social security and tax.", "Lonen correct berekenen en uitbetalen, met sociale zekerheid en belastingen.", ["You make sure every employee is paid correctly and on time each month."], ["Je zorgt dat elke medewerker elke maand correct en op tijd betaald wordt."]),
    ("onboarding", "Employee onboarding", "hr", "onboarding|employee onboarding", "inwerking|onthaal van nieuwe medewerkers", "Organising the first weeks of new employees so they become productive.", "De eerste weken van nieuwe medewerkers organiseren zodat ze snel productief zijn.", ["You make the first weeks of new colleagues smooth and well organised."], ["Je maakt de eerste weken van nieuwe collega's vlot en goed georganiseerd."]),
    ("performance-management", "Performance management", "hr", "performance management|performance reviews", "evaluatiegesprekken|prestatiebeheer", "Running review cycles and helping managers give feedback and set goals.", "Evaluatiecycli organiseren en managers helpen feedback te geven en doelen te stellen.", ["You run the yearly review cycle and help managers give useful feedback."], ["Je organiseert de jaarlijkse gesprekscyclus en helpt managers bruikbare feedback te geven."]),
    ("coaching", "Coaching", "hr", "coaching|mentoring|people development", "coachen", "Helping people grow through questions, feedback and guidance.", "Mensen laten groeien met vragen, feedback en begeleiding.", ["You help colleagues grow by asking the right questions instead of giving answers."], ["Je helpt collega's groeien door de juiste vragen te stellen in plaats van antwoorden te geven."]),
    ("hris", "HR information systems", "hr", "HRIS|HR information system|Workday|SAP SuccessFactors|SuccessFactors|Personio", "", "Maintaining employee records and HR workflows in HR software.", "Personeelsgegevens en HR-workflows beheren in HR-software.", ["You keep employee records and HR workflows correct in our HR software."], ["Je houdt personeelsdossiers en HR-workflows correct in onze HR-software."]),
    # finance
    ("financial-reporting", "Financial reporting", "finance", "financial reporting|month-end closing|year-end closing", "financiële rapportering|maandafsluiting|jaarafsluiting", "Closing the books and reporting financial results to management.", "De boeken afsluiten en financiële resultaten rapporteren aan het management.", ["You close the books every month and present the figures to management."], ["Je sluit elke maand de boeken af en presenteert de cijfers aan het management."]),
    ("budgeting", "Budgeting", "finance", "budgeting|budget control|~forecasting", "budgettering|budgetopvolging", "Preparing budgets and tracking actual spending against them.", "Budgetten opstellen en de werkelijke uitgaven ertegen opvolgen.", ["You build the yearly budget with department heads and track spending against it."], ["Je stelt met de afdelingshoofden het jaarbudget op en volgt de uitgaven ertegen op."]),
    ("accounts-payable", "Accounts payable", "finance", "accounts payable|invoice processing", "crediteurenbeheer|leveranciersboekhouding|factuurverwerking", "Checking, booking and paying supplier invoices.", "Leveranciersfacturen controleren, boeken en betalen.", ["You check and book supplier invoices and make sure they are paid on time."], ["Je controleert en boekt leveranciersfacturen en zorgt dat ze tijdig betaald worden."]),
    ("ifrs", "IFRS / Belgian GAAP", "finance", "IFRS|Belgian GAAP|BE GAAP|consolidation", "consolidatie", "Applying international and Belgian accounting standards, including group consolidation.", "Internationale en Belgische boekhoudnormen toepassen, inclusief consolidatie van de groep.", ["You apply international accounting standards when you prepare the group accounts."], ["Je past internationale boekhoudnormen toe bij het opstellen van de groepsrekeningen."]),
    ("financial-modelling", "Financial modelling", "finance", "financial modelling|financial modeling|~business cases", "financiële modellen", "Building models that project the financial outcome of decisions and investments.", "Modellen bouwen die de financiële uitkomst van beslissingen en investeringen berekenen.", ["You build models that show what an investment will return under different scenarios."], ["Je bouwt modellen die tonen wat een investering onder verschillende scenario's oplevert."]),
    ("excel", "Advanced Excel", "finance", "Excel|advanced Excel|MS Excel|pivot tables|VBA", "draaitabellen", "Working with spreadsheets: lookups, pivot tables, macros and models.", "Werken met rekenbladen: opzoekfuncties, draaitabellen, macro's en modellen.", ["You are at home in spreadsheets with lookups, pivots and macros."], ["Je bent thuis in rekenbladen met opzoekfuncties en macro's."]),
    ("controlling", "Management control", "finance", "controlling|management control|cost accounting|business controlling", "kostprijsberekening", "Analysing costs and margins and explaining variances to managers.", "Kosten en marges analyseren en afwijkingen verklaren aan managers.", ["You analyse cost per product and explain variances to plant managers."], ["Je analyseert de kostprijs per product en verklaart afwijkingen aan de plantmanagers."]),
    # cross-cutting
    ("english", "English", "cross", "English", "Engels", "Working in English, spoken and written.", "Werken in het Engels, mondeling en schriftelijk.", [], []),
    ("dutch", "Dutch", "cross", "Dutch", "Nederlands", "Working in Dutch, spoken and written.", "Werken in het Nederlands, mondeling en schriftelijk.", [], []),
    ("french", "French", "cross", "French", "Frans", "Working in French, spoken and written.", "Werken in het Frans, mondeling en schriftelijk.", [], []),
    ("german", "German", "cross", "German", "Duits", "Working in German, spoken and written.", "Werken in het Duits, mondeling en schriftelijk.", [], []),
    ("stakeholder-management", "Stakeholder management", "cross", "stakeholder management|managing stakeholders", "stakeholdermanagement", "Keeping people with different interests informed, aligned and on board.", "Mensen met verschillende belangen geïnformeerd, op één lijn en betrokken houden.", ["You keep managers from different departments aligned and informed."], ["Je houdt managers van verschillende afdelingen op één lijn en op de hoogte."]),
    ("project-management", "Project management", "cross", "project management|PRINCE2|PMP", "projectmanagement|projectbeheer", "Planning work, tracking milestones and delivering projects on time and on budget.", "Werk plannen, mijlpalen opvolgen en projecten op tijd en binnen budget opleveren.", ["You plan the work, track milestones and deliver initiatives on time and within budget."], ["Je plant het werk, volgt mijlpalen op en levert initiatieven op tijd en binnen budget op."]),
    ("agile", "Agile / Scrum", "cross", "Agile|Scrum|Kanban|Scrum Master", "", "Working in short iterations with a backlog, reviews and retrospectives.", "Werken in korte iteraties met een backlog, reviews en retrospectives.", ["You deliver in short iterations and improve the way of working after every one."], ["Je levert op in korte iteraties en verbetert de manier van werken na elke iteratie."]),
    ("communication", "Communication skills", "cross", "communication skills|~communicative", "communicatievaardigheden|communicatief", "Expressing yourself clearly to colleagues, customers and management.", "Je helder uitdrukken tegenover collega's, klanten en management.", [], []),
]

FAMILIES = {
    "software": {"en": ["Backend Developer", "Software Engineer", "DevOps Engineer", "Full-stack Developer"], "nl": ["Backend ontwikkelaar", "Software engineer", "DevOps engineer", "Full-stack ontwikkelaar"], "adjacent": ["data"]},
    "data": {"en": ["Data Analyst", "Data Engineer", "Machine Learning Engineer", "BI Developer"], "nl": ["Data-analist", "Data engineer", "Machine learning engineer", "BI-ontwikkelaar"], "adjacent": ["software"]},
    "maintenance": {"en": ["Maintenance Technician", "Electromechanic", "Maintenance Engineer"], "nl": ["Onderhoudstechnicus", "Elektromecanicien", "Onderhoudsingenieur"], "adjacent": ["production"]},
    "production": {"en": ["Production Supervisor", "Quality Coordinator", "Production Planner"], "nl": ["Productieverantwoordelijke", "Kwaliteitscoördinator", "Productieplanner"], "adjacent": ["maintenance", "logistics"]},
    "logistics": {"en": ["Warehouse Supervisor", "Supply Chain Planner", "Logistics Coordinator", "Purchaser"], "nl": ["Magazijnverantwoordelijke", "Supply chain planner", "Logistiek coördinator", "Aankoper"], "adjacent": ["production"]},
    "sales": {"en": ["Account Manager", "Sales Engineer", "Inside Sales Representative"], "nl": ["Accountmanager", "Sales engineer", "Binnendienstmedewerker verkoop"], "adjacent": ["logistics"]},
    "hr": {"en": ["HR Business Partner", "Talent Partner", "HR Officer"], "nl": ["HR-business partner", "Talent partner", "HR-medewerker"], "adjacent": ["finance"]},
    "finance": {"en": ["Financial Controller", "Accountant", "Finance Analyst"], "nl": ["Financieel controller", "Boekhouder", "Financieel analist"], "adjacent": ["hr"]},
}

CROSS_FOR = {
    "software": ["english", "agile", "dutch"], "data": ["english", "stakeholder-management", "dutch"],
    "maintenance": ["dutch", "french", "english"], "production": ["dutch", "french", "communication"],
    "logistics": ["dutch", "french", "english", "german"], "sales": ["dutch", "french", "english", "german", "communication"],
    "hr": ["dutch", "french", "stakeholder-management", "communication"], "finance": ["dutch", "english", "project-management"],
}

# Skills that companies talk about in "about us" or "what we offer" without requiring them.
# Each sentence names the skill (or an ambiguous alias of it) but asks nothing of the candidate.
COMPANY_TALK = {
    "sap-logistics": {"about": {"en": ["Our plants run on SAP.", "Our IT department is moving to S/4HANA this year."], "nl": ["Onze fabrieken draaien op SAP.", "Onze IT-afdeling stapt dit jaar over naar S/4HANA."]}},
    "lean-manufacturing": {"about": {"en": ["We are proud of our lean culture.", "Continuous improvement is part of our DNA."], "nl": ["We zijn trots op onze lean cultuur.", "Continu verbeteren zit in ons DNA."]},
                           "offer": {"en": ["Training in lean manufacturing."], "nl": ["Een opleiding lean manufacturing."]}},
    "workplace-safety": {"about": {"en": ["Safety comes first at every Haldane site."], "nl": ["Veiligheid staat voorop op elke Haldane-site."]},
                         "offer": {"en": ["A VCA course in your first month."], "nl": ["Een VCA-opleiding in je eerste maand."]}},
    "aws": {"about": {"en": ["Our IT platform runs on AWS."], "nl": ["Ons IT-platform draait op AWS."]}},
    "iso-9001": {"about": {"en": ["All our plants are ISO 9001 certified."], "nl": ["Al onze fabrieken zijn ISO 9001-gecertificeerd."]}},
    "food-safety": {"about": {"en": ["Food safety is non-negotiable in our ingredient plants."], "nl": ["Voedselveiligheid is heilig in onze ingrediëntenfabrieken."]}},
    "docker": {"about": {"en": ["We ship around 400 containers a week through the port of Antwerp."], "nl": ["We verschepen elke week zo'n 400 containers via de haven van Antwerpen."]}},
    "nlp": {"about": {"en": ["Our Ghent plant makes transformers for the energy grid."], "nl": ["Onze fabriek in Gent maakt transformers voor het elektriciteitsnet."]}},
    "coaching": {"offer": {"en": ["Personal coaching and a training budget.", "Mentoring by an experienced colleague."], "nl": ["Persoonlijke coaching en een opleidingsbudget.", "Mentoring door een ervaren collega."]}},
    "agile": {"about": {"en": ["Our digital team works in Scrum."], "nl": ["Ons digitale team werkt in Scrum."]}},
    "english": {"offer": {"en": ["Free English lessons."], "nl": ["Gratis lessen Engels."]}},
}

# ------------------------------------------------------------------ templates
T = {
    "en": {
        "headings": {
            "about": ["About Haldane", "Who we are"], "resp": ["Your role", "Responsibilities", "What you will do"],
            "req": ["What you bring", "Your profile", "Requirements"], "pref": ["Nice to have", "Bonus points"],
            "offer": ["What we offer", "Our offer"],
        },
        "intro": ["Haldane Group makes packaging, food ingredients and machine parts in {n} plants across Belgium.", "Haldane is a family-owned industrial group with {n} sites in Flanders and Wallonia."],
        "resp": ["You will work daily with {a}.", "You take ownership of {a} for the site.", "You use {a} to support the team."],
        "req": ["You have at least {n} years of experience with {a}.", "Solid knowledge of {a} is a must.", "You are comfortable working with {a}.", "Hands-on experience with {a}."],
        "req2": ["You bring experience in {a} and {b}.", "You know your way around {a} and {b}."],
        "lang": ["You speak fluent {a}.", "Good knowledge of {a} is required."],
        "pref": ["Experience with {a} is a plus.", "Familiarity with {a} is a bonus.", "Knowledge of {a} would be nice."],
        "neg": ["No prior experience with {a} is required.", "You don't need to know {a}; we train you.", "Experience with {a} is not necessary."],
        "offer": ["A competitive salary, meal vouchers and a company car.", "Flexible hours and 32 days off.", "A permanent contract in a stable company."],
        "contact": ["Questions? Contact {name}, our HR partner."],
        "title_suffix": ["", ""],
    },
    "nl": {
        "headings": {
            "about": ["Over Haldane", "Wie zijn we"], "resp": ["Jouw rol", "Takenpakket", "Wat ga je doen"],
            "req": ["Jouw profiel", "Wat breng je mee", "Vereisten"], "pref": ["Pluspunten", "Een plus"],
            "offer": ["Wat wij bieden", "Ons aanbod"],
        },
        "intro": ["Haldane Group maakt verpakkingen, voedingsingrediënten en machineonderdelen in {n} fabrieken in België.", "Haldane is een industriële familiegroep met {n} sites in Vlaanderen en Wallonië."],
        "resp": ["Je werkt dagelijks met {a}.", "Je bent verantwoordelijk voor {a} op de site.", "Je gebruikt {a} om het team te ondersteunen."],
        "req": ["Je hebt minstens {n} jaar ervaring met {a}.", "Een grondige kennis van {a} is een must.", "Je werkt vlot met {a}.", "Praktische ervaring met {a}."],
        "req2": ["Je hebt ervaring met {a} en {b}.", "Je bent thuis in {a} en {b}."],
        "lang": ["Je spreekt vlot {a}.", "Een goede kennis van het {a} is vereist."],
        "pref": ["Ervaring met {a} is een pluspunt.", "Kennis van {a} is mooi meegenomen.", "Je kent {a}? Dan is dat een troef."],
        "neg": ["Ervaring met {a} is geen vereiste.", "Je hoeft {a} niet te kennen, wij leiden je op.", "Kennis van {a} is niet nodig."],
        "offer": ["Een competitief loon, maaltijdcheques en een bedrijfswagen.", "Flexibele uren en 32 verlofdagen.", "Een vast contract in een stabiel bedrijf."],
        "contact": ["Vragen? Neem contact op met {name}, onze HR-partner."],
        "title_suffix": [" (m/v/x)", ""],
    },
}

# Coded language. "lex" = the product's checker knows this phrase; the rest measures what it misses.
CODED = {
    "en": [("age", "Join our young and dynamic team.", True), ("age", "You are a digital native.", True), ("age", "Recent graduates are preferred.", False),
           ("gender", "He will report to the plant manager.", True), ("gender", "The ideal candidate is a hands-on guy.", True),
           ("origin", "You are a native speaker.", True)],
    "nl": [("age", "Je komt terecht in een jong en dynamisch team.", True), ("age", "Je bent maximaal 30 jaar.", True), ("age", "Je bent een jonge starter.", False),
           ("gender", "Hij rapporteert aan de plantmanager.", True), ("gender", "Je bent een echte vakman.", True),
           ("origin", "Je bent een native speaker.", True)],
}
COUNTERFACTUAL = {
    "en": {"gender": ("He will report to the plant manager.", "She will report to the plant manager."), "age": "Join our young and dynamic team."},
    "nl": {"gender": ("Hij rapporteert aan de plantmanager.", "Zij rapporteert aan de plantmanager."), "age": "Je komt terecht in een jong en dynamisch team."},
}
NAMES = [("Pieter Claes", "Fatima El Amrani"), ("Sofie Peeters", "Mohamed Benali"), ("Lucas Dubois", "Elif Yilmaz"), ("Jonas Maes", "Aisha Diallo")]


# ------------------------------------------------------------------ independent alias scan (oracle side)
def fold(text: str) -> str:
    out = []
    for ch in text:
        d = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c)).lower()
        out.append(d[:1] if d else " ")
    return "".join(out)


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#]+", fold(text))


def alias_table() -> list[tuple[tuple[str, ...], str]]:
    rows = []
    for sid, label, _fam, en, nl, *_ in SKILLS:
        for raw in [label] + [a for a in (en.split("|") + nl.split("|")) if a]:
            rows.append((tuple(tokens(raw.lstrip("~"))), sid))
    return rows


ALIASES = alias_table()


def skills_in(sentence: str) -> set[str]:
    """Skills whose alias appears in the sentence. An alias inside a longer alias of
    another skill does not count ("SAP" inside "SAP SuccessFactors")."""
    toks = tokens(sentence)
    hits = []
    for seq, sid in ALIASES:
        n = len(seq)
        hits += [(i, i + n, sid) for i in range(len(toks) - n + 1) if tuple(toks[i:i + n]) == seq]
    return {sid for s, e, sid in hits
            if not any(s2 <= s and e <= e2 and (e2 - s2) > (e - s) and sid2 != sid for s2, e2, sid2 in hits)}


# ------------------------------------------------------------------ build the taxonomy
def taxonomy() -> dict:
    by_family: dict[str, list[str]] = {}
    for sid, _l, fam, *_ in SKILLS:
        by_family.setdefault(fam, []).append(sid)
    skills = []
    for sid, label, fam, en, nl, d_en, d_nl, _p_en, _p_nl in SKILLS:
        aliases = []
        for lang, raw in (("en", en), ("nl", nl)):
            for a in [x for x in raw.split("|") if x]:
                aliases.append({"text": a.lstrip("~"), "lang": lang, "ambiguous": a.startswith("~")})
        if not any(a["text"].lower() == label.lower() for a in aliases):
            aliases.insert(0, {"text": label, "lang": "en", "ambiguous": False})
        fam_list = by_family[fam]
        i = fam_list.index(sid)
        related = [s for s in (fam_list[i - 1] if i > 0 else None, fam_list[i + 1] if i + 1 < len(fam_list) else None) if s]
        if fam == "cross":  # knowing English does not make Dutch "close to learn"
            related = []
        skills.append({"id": sid, "label": label, "family": fam, "aliases": aliases,
                       "definition": {"en": d_en, "nl": d_nl}, "related": related})
    return {"version": TAXONOMY_VERSION, "skills": skills}


# ------------------------------------------------------------------ job descriptions
SKILL = {row[0]: row for row in SKILLS}


def surface(rng: random.Random, sid: str, lang: str) -> tuple[str, str]:
    """A display alias of the skill in this language (or the shared English alias)."""
    _sid, label, _f, en, nl, *_ = SKILL[sid]
    pool = [a for a in (nl.split("|") if lang == "nl" else []) if a and not a.startswith("~")]
    pool += [a for a in en.split("|") if a and not a.startswith("~")]
    if sid in ("english", "dutch", "french", "german"):
        pool = [a for a in (nl if lang == "nl" else en).split("|") if a]
    if rng.random() < 0.25 and sid not in ("english", "dutch", "french", "german"):
        return label, "label"
    native = [a for a in (nl.split("|") if lang == "nl" else []) if a and not a.startswith("~")]
    if native and rng.random() < 0.6:
        return rng.choice(native), "alias"
    return rng.choice(pool), "alias"


def paraphrase(rng: random.Random, sid: str, lang: str) -> str | None:
    p_en, p_nl = SKILL[sid][7], SKILL[sid][8]
    pool = p_nl if lang == "nl" else p_en
    return rng.choice(pool) if pool else None


class Doc:
    def __init__(self) -> None:
        self.text = ""
        self.sentences: list[dict] = []

    def line(self, text: str, kind: str, section: str, expect: set[str], **meta) -> tuple[int, int]:
        if self.text:
            self.text += "\n"
        start = len(self.text)
        self.text += text
        found = skills_in(text)
        if found != expect:
            raise AssertionError(f"sentence {text!r}: expected aliases {sorted(expect)}, found {sorted(found)}")
        self.sentences.append({"start": start, "end": len(self.text), "kind": kind, "section": section, **meta})
        return start, len(self.text)


def make_jd(rng: random.Random, idx: int, split: str) -> dict:
    lang = "nl" if rng.random() < 0.35 else "en"
    fam = rng.choice(list(FAMILIES))
    t = T[lang]
    headings = rng.random() >= 0.2
    core = [s for s, *_ in [r for r in SKILLS if r[2] == fam]]
    adjacent = [r[0] for r in SKILLS if r[2] in FAMILIES[fam]["adjacent"]]
    n_req = rng.randint(4, 6)
    req = rng.sample(core, min(n_req, len(core)))
    req += rng.sample(CROSS_FOR[fam], rng.randint(1, 2))
    rest = [s for s in core + adjacent if s not in req]
    pref = rng.sample(rest, rng.randint(1, 3))
    gold_ids = set(req) | set(pref)

    about_pool = [s for s, v in COMPANY_TALK.items() if "about" in v and s not in gold_ids]
    about_skill = rng.choice(about_pool) if rng.random() < 0.6 else None
    offer_pool = [s for s, v in COMPANY_TALK.items() if "offer" in v and s not in gold_ids and s != about_skill]
    offer_skill = rng.choice(offer_pool) if offer_pool and rng.random() < 0.35 else None
    neg_pool = [s for s in core + adjacent if s not in gold_ids and s not in (about_skill, offer_skill)]
    neg_skill = rng.choice(neg_pool) if neg_pool and rng.random() < 0.4 else None
    coded = rng.choice(CODED[lang]) if rng.random() < 0.2 else None

    title = rng.choice(FAMILIES[fam][lang]) + rng.choice(t["title_suffix"])
    gold: dict[str, dict] = {}
    distractors: list[dict] = []
    flags: list[dict] = []
    d = Doc()

    def add_gold(sid: str, importance: str, span: tuple[int, int], how: str) -> None:
        g = gold.setdefault(sid, {"id": sid, "importance": importance, "spans": [], "surface": how})
        g["spans"].append(list(span))
        if importance == "required":
            g["importance"] = "required"

    tspan = d.line(title, "title", "title", skills_in(title))
    for sid in skills_in(title):
        add_gold(sid, "required", tspan, "title")
        gold_ids.add(sid)

    def heading(key: str, section: str) -> None:
        if headings:
            d.line(rng.choice(t["headings"][key]), "heading", section, set())

    # about us
    heading("about", "about")
    d.line(rng.choice(t["intro"]).format(n=rng.randint(4, 9)), "boilerplate", "about", set())
    if about_skill:
        span = d.line(rng.choice(COMPANY_TALK[about_skill]["about"][lang]), "distractor", "about", {about_skill})
        distractors.append({"id": about_skill, "kind": "about", "span": list(span)})
    if coded and coded[0] in ("age",):
        span = d.line(coded[1], "coded", "about", set())
        flags.append({"category": coded[0], "phrase": coded[1], "span": list(span), "in_lexicon": coded[2]})

    # responsibilities and requirements
    order = req[:]
    rng.shuffle(order)
    resp_n = rng.randint(1, max(1, len(order) // 2))
    resp, profile = order[:resp_n], order[resp_n:]
    heading("resp", "resp")
    for sid in resp:
        para = paraphrase(rng, sid, lang)
        if para and rng.random() < 0.6:
            span = d.line(para, "paraphrase", "resp", set())
            add_gold(sid, "required", span, "paraphrase")
        else:
            a, how = surface(rng, sid, lang)
            span = d.line(rng.choice(t["resp"]).format(a=a), "mention", "resp", {sid})
            add_gold(sid, "required", span, how)
    if coded and coded[0] == "gender":
        span = d.line(coded[1], "coded", "resp", set())
        flags.append({"category": coded[0], "phrase": coded[1], "span": list(span), "in_lexicon": coded[2]})
    heading("req", "req")
    i = 0
    while i < len(profile):
        sid = profile[i]
        if sid in ("english", "dutch", "french", "german"):
            a, how = surface(rng, sid, lang)
            span = d.line(rng.choice(t["lang"]).format(a=a), "mention", "req", {sid})
            add_gold(sid, "required", span, how)
            i += 1
            continue
        nxt = profile[i + 1] if i + 1 < len(profile) else None
        if nxt and nxt not in ("english", "dutch", "french", "german") and rng.random() < 0.25:
            (a, how_a), (b, how_b) = surface(rng, sid, lang), surface(rng, nxt, lang)
            span = d.line(rng.choice(t["req2"]).format(a=a, b=b), "mention", "req", {sid, nxt})
            add_gold(sid, "required", span, how_a)
            add_gold(nxt, "required", span, how_b)
            i += 2
            continue
        para = paraphrase(rng, sid, lang)
        if para and rng.random() < 0.3:
            span = d.line(para, "paraphrase", "req", set())
            add_gold(sid, "required", span, "paraphrase")
        else:
            a, how = surface(rng, sid, lang)
            span = d.line(rng.choice(t["req"]).format(a=a, n=rng.randint(2, 6)), "mention", "req", {sid})
            add_gold(sid, "required", span, how)
        i += 1
    if neg_skill:
        a = surface(rng, neg_skill, lang)[0]
        span = d.line(rng.choice(t["neg"]).format(a=a), "negated", "req", {neg_skill})
        distractors.append({"id": neg_skill, "kind": "negated", "span": list(span)})
    if coded and coded[0] == "origin":
        span = d.line(coded[1], "coded", "req", set())
        flags.append({"category": coded[0], "phrase": coded[1], "span": list(span), "in_lexicon": coded[2]})

    heading("pref", "pref")
    for sid in pref:
        para = paraphrase(rng, sid, lang)
        if para and rng.random() < 0.25:
            span = d.line(para, "paraphrase", "pref", set())
            add_gold(sid, "preferred", span, "paraphrase")
        else:
            a, how = surface(rng, sid, lang)
            span = d.line(rng.choice(t["pref"]).format(a=a), "mention", "pref", {sid})
            add_gold(sid, "preferred", span, how)

    heading("offer", "offer")
    d.line(rng.choice(t["offer"]), "boilerplate", "offer", set())
    if offer_skill:
        span = d.line(rng.choice(COMPANY_TALK[offer_skill]["offer"][lang]), "distractor", "offer", {offer_skill})
        distractors.append({"id": offer_skill, "kind": "offer", "span": list(span)})
    name = rng.choice(rng.choice(NAMES))
    d.line(rng.choice(t["contact"]).format(name=name), "contact", "offer", set())

    return {
        "id": f"JD-{idx:03d}", "split": split, "lang": lang, "family": fam, "title": title,
        "headings": headings, "text": d.text, "contact": name,
        "gold": {"skills": sorted(gold.values(), key=lambda g: g["id"]), "distractors": distractors, "flags": flags},
        "sentences": d.sentences,
    }


def counterfactuals(jd: dict) -> list[dict]:
    """Three variants that must not change the inferred skills."""
    lang, text = jd["lang"], jd["text"]
    out = []
    he, she = COUNTERFACTUAL[lang]["gender"]
    lines = text.split("\n")
    # gender: add the same sentence with "he" and with "she" after the title
    for variant, sentence in (("he", he), ("she", she)):
        out.append({"id": f"{jd['id']}-gender-{variant}", "base": jd["id"], "kind": "gender", "variant": variant,
                    "text": "\n".join([lines[0], sentence, *lines[1:]])})
    # name: swap the contact person for the other name in the same pair
    other = next(b if a == jd["contact"] else a for a, b in NAMES if jd["contact"] in (a, b))
    out.append({"id": f"{jd['id']}-name", "base": jd["id"], "kind": "name", "variant": other,
                "text": text.replace(jd["contact"], other)})
    # age: add an age-coded sentence after the title
    out.append({"id": f"{jd['id']}-age", "base": jd["id"], "kind": "age", "variant": "young",
                "text": "\n".join([lines[0], COUNTERFACTUAL[lang]["age"], *lines[1:]])})
    return out


def people(rng: random.Random) -> list[dict]:
    rows = []
    fams = list(FAMILIES)
    for i in range(60):
        fam = fams[i % len(fams)]
        core = [r[0] for r in SKILLS if r[2] == fam]
        adjacent = [r[0] for r in SKILLS if r[2] in FAMILIES[fam]["adjacent"]]
        skills = rng.sample(core, rng.randint(3, min(7, len(core))))
        skills += rng.sample(adjacent, rng.randint(0, 2))
        skills += rng.sample(CROSS_FOR[fam], rng.randint(1, 2))
        rows.append({"id": f"EMP-{i + 1:03d}", "home_family": fam, "skills": sorted(set(skills))})
    return rows


# ------------------------------------------------------------------ CVs (phase 2: people)
# Fictional people. Names, streets, phone numbers and register numbers are generated; e-mail
# addresses use the reserved .example domain. Two name groups make the counterfactual swap.
FIRST = {"a": ["Pieter", "Sofie", "Jonas", "Lotte", "Wouter", "Hanne", "Bram", "Elke", "Thomas", "Lien"],
         "b": ["Mohamed", "Fatima", "Yusuf", "Aisha", "Elif", "Karim", "Nadia", "Emre", "Samira", "Bilal"]}
LAST = {"a": ["Claes", "Peeters", "Maes", "Janssens", "Wouters", "Vermeulen", "De Smet", "Lambrecht"],
        "b": ["El Amrani", "Benali", "Yilmaz", "Diallo", "Kaya", "Bouzid", "Haddad", "Mensah"]}
STREETS = ["Kerkstraat", "Stationsstraat", "Molenstraat", "Lindelaan", "Beukendreef", "Kapelleweg", "Marktplein", "Brusselsesteenweg"]
CITIES = [("9000", "Gent"), ("8500", "Kortrijk"), ("2000", "Antwerpen"), ("8000", "Brugge"), ("3000", "Leuven"), ("9300", "Aalst")]
EMPLOYERS = ["Vanbrabant Food", "Leiedal Metaal", "Scheldepoort Logistics", "Mosterdhuis Industries", "Haldane Group", "Kanaalzone Plastics"]
CV_T = {
    "en": {"profile": ["Profile", "About me"], "experience": ["Experience", "Work experience"], "skills": ["Skills"],
           "languages": ["Languages"], "education": ["Education", "Courses"], "interests": ["Interests"],
           "intro": "{title} with {n} years of experience.", "born": "Born ",  "nid": "National register number: ",
           "bullet": ["- Worked daily with {a}.", "- Responsible for {a} at the {city} site.", "- Introduced {a} for a team of {n}."],
           "aspire": ["I would like to learn {a}.", "Next step for me: a course in {a}."],
           "neg": ["No hands-on experience with {a} yet."],
           "cert": "Certificate: {a} ({y})", "degree": ["Professional bachelor in Electromechanics ({y})", "Bachelor in Business Administration ({y})", "Secondary school, technical track ({y})"],
           "hobby": ["Cycling, cooking and photography.", "Running and board games."],
           "level": {"native": "native", "fluent": "fluent", "good": "good"}},
    "nl": {"profile": ["Profiel", "Over mij"], "experience": ["Werkervaring", "Ervaring"], "skills": ["Vaardigheden"],
           "languages": ["Talen"], "education": ["Opleiding", "Opleidingen"], "interests": ["Interesses", "Hobby's"],
           "intro": "{title} met {n} jaar ervaring.", "born": "Geboren op ", "nid": "Rijksregisternummer: ",
           "bullet": ["- Werkte dagelijks met {a}.", "- Verantwoordelijk voor {a} op de site in {city}.", "- Voerde {a} in voor een team van {n}."],
           "aspire": ["Ik wil graag {a} leren.", "Volgende stap voor mij: een opleiding {a}."],
           "neg": ["Nog geen praktijkervaring met {a}."],
           "cert": "Attest: {a} ({y})", "degree": ["Professionele bachelor Elektromechanica ({y})", "Bachelor Bedrijfsmanagement ({y})", "Secundair onderwijs, technische richting ({y})"],
           "hobby": ["Fietsen, koken en fotografie.", "Lopen en gezelschapsspellen."],
           "level": {"native": "moedertaal", "fluent": "vlot", "good": "goed"}},
}


def ascii_fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def person(rng: random.Random, group: str) -> dict:
    first, last = rng.choice(FIRST[group]), rng.choice(LAST[group])
    year = rng.randint(1966, 2000)
    month, day = rng.randint(1, 12), rng.randint(1, 28)
    return {"name": f"{first} {last}", "email": ascii_fold(f"{first}.{last}").lower().replace(" ", "") + "@mail.example",
            "street": f"{rng.choice(STREETS)} {rng.randint(1, 140)}", "city": rng.choice(CITIES),
            "phone": f"04{rng.randint(70, 99)} {rng.randint(10, 99)} {rng.randint(10, 99)} {rng.randint(10, 99)}",
            "born": (day, month, year), "nid_tail": f"{rng.randint(100, 999)}.{rng.randint(10, 99)}", "group": group}


def header_lines(p: dict, lang: str, with_nid: bool) -> list[list[tuple[str, str | None]]]:
    d, m, y = p["born"]
    pc, city = p["city"]
    lines = [[(p["name"], "name")],
             [(f"{p['street']}, {pc} {city}", "address"), (" · ", None), (p["phone"], "phone"), (" · ", None), (p["email"], "email")],
             [(CV_T[lang]["born"], None), (f"{d:02d}/{m:02d}/{y}", "birthdate")]]
    if with_nid:
        lines.append([(CV_T[lang]["nid"], None), (f"{y % 100:02d}.{m:02d}.{d:02d}-{p['nid_tail']}", "national_id")])
    return lines


def cv_paraphrase(rng: random.Random, sid: str, lang: str) -> str | None:
    para = paraphrase(rng, sid, lang)
    if not para:
        return None
    body = para.split(" ", 1)[1]  # drop "You" / "Je"
    return "- " + body[0].upper() + body[1:]


def make_cv(rng: random.Random, idx: int, split: str) -> dict:
    lang = "nl" if rng.random() < 0.4 else "en"
    fam = rng.choice(list(FAMILIES))
    t = CV_T[lang]
    p = person(rng, rng.choice("ab"))
    core = [r[0] for r in SKILLS if r[2] == fam]
    adjacent = [r[0] for r in SKILLS if r[2] in FAMILIES[fam]["adjacent"]]
    held = rng.sample(core, rng.randint(4, min(7, len(core))))
    listed = rng.sample([s for s in core + adjacent if s not in ("english", "dutch", "french", "german")], rng.randint(2, 3))
    langs = rng.sample(["dutch", "english", "french", "german"], rng.randint(1, 3))
    cert = rng.choice([s for s in core + adjacent]) if rng.random() < 0.35 else None
    not_held = [s for s in core + adjacent if s not in held + listed + langs + [cert]]
    aspire = rng.choice(not_held) if not_held and rng.random() < 0.5 else None
    neg = rng.choice([s for s in not_held if s != aspire]) if rng.random() < 0.3 else None
    d = Doc()
    gold: dict[str, dict] = {}
    pii: list[dict] = []

    def add(sid: str, span: tuple[int, int], how: str) -> None:
        g = gold.setdefault(sid, {"id": sid, "importance": "required", "spans": [], "surface": how})
        g["spans"].append(list(span))

    for parts in header_lines(p, lang, rng.random() < 0.25):
        line = "".join(x for x, _ in parts)
        start, _ = d.line(line, "header", "header", set())
        pos = start
        for text, kind in parts:
            if kind:
                pii.append({"kind": kind, "start": pos, "end": pos + len(text), "value": text})
            pos += len(text)

    def heading(key: str) -> None:
        d.line(rng.choice(t[key]), "heading", key, set())

    title = rng.choice(FAMILIES[fam][lang])
    heading("profile")
    span = d.line(t["intro"].format(title=title, n=rng.randint(2, 20)), "intro", "profile", skills_in(title))
    for sid in skills_in(title):
        add(sid, span, "title")
    distractors = []
    if aspire:
        a = surface(rng, aspire, lang)[0]
        span = d.line(rng.choice(t["aspire"]).format(a=a), "aspiration", "profile", {aspire})
        distractors.append({"id": aspire, "kind": "aspiration", "span": list(span)})

    heading("experience")
    order = held[:]
    rng.shuffle(order)
    jobs = [order[: len(order) // 2], order[len(order) // 2:]]
    year = 2026
    for job in jobs:
        y2, y1 = year, year - rng.randint(2, 6)
        year = y1
        jt = rng.choice(FAMILIES[fam][lang])
        span = d.line(f"{jt} · {rng.choice(EMPLOYERS)} · {y1}–{y2}", "job", "experience", skills_in(jt))
        for sid in skills_in(jt):
            add(sid, span, "title")
        for sid in job:
            para = cv_paraphrase(rng, sid, lang)
            if para and rng.random() < 0.35:
                span = d.line(para, "paraphrase", "experience", set())
                add(sid, span, "paraphrase")
            else:
                a, how = surface(rng, sid, lang)
                span = d.line(rng.choice(t["bullet"]).format(a=a, city=p["city"][1], n=rng.randint(4, 15)), "mention", "experience", {sid})
                add(sid, span, how)
    if neg:
        a = surface(rng, neg, lang)[0]
        span = d.line(rng.choice(t["neg"]).format(a=a), "negated", "experience", {neg})
        distractors.append({"id": neg, "kind": "negated", "span": list(span)})

    heading("skills")
    names = [surface(rng, sid, lang) for sid in listed]
    line = ", ".join(n for n, _ in names)
    span = d.line(line, "list", "skills", set(listed))
    for sid, (_, how) in zip(listed, names):
        add(sid, span, how)

    heading("languages")
    levels = list(t["level"].values())
    parts = []
    for sid in langs:
        a = surface(rng, sid, lang)[0]
        parts.append(f"{a} ({rng.choice(levels)})")
    span = d.line(", ".join(parts), "list", "languages", set(langs))
    for sid in langs:
        add(sid, span, "alias")

    heading("education")
    d.line(rng.choice(t["degree"]).format(y=p["born"][2] + rng.randint(18, 23)), "degree", "education", set())
    if cert:
        a = surface(rng, cert, lang)[0]
        span = d.line(t["cert"].format(a=a, y=rng.randint(max(2012, p["born"][2] + 20), 2025)), "cert", "education", {cert})
        add(cert, span, "certificate")

    heading("interests")
    d.line(rng.choice(t["hobby"]), "hobby", "interests", set())
    return {"id": f"CV-{idx:03d}", "split": split, "lang": lang, "family": fam, "text": d.text, "person": p,
            "gold": {"skills": sorted(gold.values(), key=lambda g: g["id"]), "distractors": distractors, "pii": pii}}


def cv_counterfactuals(cv: dict, rng: random.Random) -> list[dict]:
    """Same CV, other person: a name from the other group, or a birth year 30 years apart."""
    p = cv["person"]
    other = person(rng, "b" if p["group"] == "a" else "a")
    swapped = cv["text"].replace(p["name"], other["name"]).replace(p["email"], other["email"])
    d, m, y = p["born"]
    y2 = y - 30 if y >= 1996 else y + 30 if y <= 1970 else (1966 if y > 1983 else 1999)
    aged = cv["text"].replace(f"{d:02d}/{m:02d}/{y}", f"{d:02d}/{m:02d}/{y2}").replace(f"{y % 100:02d}.{m:02d}.{d:02d}-", f"{y2 % 100:02d}.{m:02d}.{d:02d}-")
    return [{"id": f"{cv['id']}-name", "base": cv["id"], "kind": "name", "split": cv["split"], "text": swapped},
            {"id": f"{cv['id']}-age", "base": cv["id"], "kind": "age", "split": cv["split"], "text": aged}]


def build() -> dict[str, str]:
    rng = random.Random(SEED)
    jds = []
    for i in range(1, 301):
        split = "train" if i <= 150 else "dev" if i <= 200 else "test"
        jds.append(make_jd(rng, i, split))
    cfs = [cf | {"split": jd["split"]} for jd in jds if jd["split"] in ("dev", "test") for cf in counterfactuals(jd)]
    files = {
        "taxonomy.json": json.dumps(taxonomy(), ensure_ascii=False, indent=1) + "\n",
        "job_descriptions.jsonl": "".join(json.dumps(j, ensure_ascii=False) + "\n" for j in jds),
        "counterfactuals.jsonl": "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cfs),
        "people.jsonl": "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in people(rng)),
    }
    rng_cv = random.Random(SEED + 7)  # separate stream: adding CVs leaves the job descriptions unchanged
    cvs = [make_cv(rng_cv, i, "train" if i <= 80 else "dev" if i <= 110 else "test") for i in range(1, 161)]
    ccf = [cf for cv in cvs if cv["split"] in ("dev", "test") for cf in cv_counterfactuals(cv, rng_cv)]
    files["cvs.jsonl"] = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cvs)
    files["cv_counterfactuals.jsonl"] = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in ccf)
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    files = build()
    stale = []
    for name, content in files.items():
        path = DATA / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        print("stale data: " + ", ".join(stale) + " (run python3 scripts/make_data.py)")
        return 1
    jds = [json.loads(line) for line in files["job_descriptions.jsonl"].splitlines()]
    print(f"{'checked' if args.check else 'wrote'}: {len(json.loads(files['taxonomy.json'])['skills'])} skills, "
          f"{len(jds)} job descriptions, {files['counterfactuals.jsonl'].count(chr(10))} counterfactuals, "
          f"{files['people.jsonl'].count(chr(10))} people, {files['cvs.jsonl'].count(chr(10))} CVs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
