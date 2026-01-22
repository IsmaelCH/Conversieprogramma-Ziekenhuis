# SAP Data Migratie Tool

Tool voor het converteren van legacy ziekenhuisdata naar SAP importformaat.

## Installatie
Zorg dat Python geïnstalleerd is. Installeer daarna de benodigdheden:

```bash
pip install -r requirements.txt
```

## Gebruik

### 1. Grafische Interface (GUI)
Start de webapplicatie om interactief bestanden te converteren en mappings te beheren:

```bash
streamlit run main_gui.py
```
*Of als dat niet werkt:*
```bash
python -m streamlit run main_gui.py
```

### 2. Batch Verwerking (Automatisch)
Voor het in één keer verwerken van alle bestanden in een map:

```bash
python run_batch.py --input data/input --output data/output
```

Optioneel kun je een peildatum meegeven:
```bash
python run_batch.py --input data/input --output data/output --date 2025-12-31
```

## Projectstructuur
* **`main_gui.py`**: De gebruikersinterface (Streamlit).
* **`run_batch.py`**: Script voor automatische bulkverwerking.
* **`backend/`**: Bevat de conversielogica (voorheen `src/`).
* **`settings.json`**: Configuratie voor mappings en regels (voorheen `config.json`).
* **`data/`**: Mappen voor input, output en mappings.