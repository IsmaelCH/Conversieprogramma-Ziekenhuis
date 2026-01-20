# CONTEXT VOOR COPILOT:
# Project: SAP Data Migratie Tool (ETL).
# Stack: Python, Pandas, Streamlit, Streamlit-AgGrid.
# Doel: Converteer legacy ziekenhuisdata (Artikels.csv + Locatie.csv) naar SAP formaat.
# Regels:
# 1. Config: Mappings en regels staan in 'config.json'.
# 2. Input: Join 'Locatie' (leidend) met 'Artikels' op 'ArtikelNr'.
# 3. Logica: 'WERKS' komt uit bestandsnaam (bv. ZH01).
# 4. Filter: Verwijder records waar 'Actief'='N' OF 'EindDat' < gekozen datum.
# 5. Output: De kolommen moeten exact matchen met 'Opdracht_template_MATMAS.xlsx'.
# Huidige taak: Implementeer de datum-filter logica en lees de template in om de output kolommen te forceren.

import pandas as pd
import os
import json
from datetime import datetime

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def run_conversion(source_file_path, peildatum=None):
    """
    Converteert data naar SAP formaat.
    :param source_file_path: Pad naar het bronbestand.
    :param peildatum: (Optioneel) Datum object of string (YYYY-MM-DD). 
                      Artikelen met EindDat < peildatum worden gefilterd.
                      Als None, wordt 'vandaag' gebruikt.
    """
    config = load_config()
    if peildatum is None:
        peildatum = datetime.now()
    peildatum = pd.to_datetime(peildatum)
    filename = os.path.basename(source_file_path)
    vestiging_code = filename.split('_')[-1].split('.')[0]

    # 1. Data inlezen
    df_art = pd.read_excel(source_file_path, sheet_name='Artikels')
    df_loc = pd.read_excel(source_file_path, sheet_name='Locatie')
    df_art.columns = df_art.columns.str.strip()
    df_loc.columns = df_loc.columns.str.strip()

    # 2. Join
    df_merged = pd.merge(df_loc, df_art, on='ArtikelNr', how='left')

    # 3. Filter: Actief == 'J' en EindDat niet in het verleden t.o.v. peildatum
    if 'EindDat' in df_merged.columns:
        df_merged['EindDat'] = pd.to_datetime(df_merged['EindDat'], errors='coerce')
    filter_condition = (
        (df_merged['Actief'] == 'J') & 
        (
            (df_merged['EindDat'].isna()) |
            (df_merged['EindDat'] >= peildatum)
        )
    )
    df_filtered = df_merged[filter_condition].copy()
    print(f"Rijen voor filter: {len(df_merged)}")
    print(f"Rijen na filter (Actief='J' & Datum > {peildatum.date()}): {len(df_filtered)}")

    # 4. Transformatie naar SAP formaat
    mappings = config['mappings']
    sap_output = pd.DataFrame()
    sap_output['WERKS'] = vestiging_code
    sap_output['MATNR'] = df_filtered[mappings['MATNR']['source']]
    sap_output['MAKTX'] = df_filtered[mappings['MAKTX']['source']]
    map_uom = pd.read_excel(os.path.join(config['mapping_folder'], mappings['MEINS']['map_file']), sheet_name=mappings['MEINS']['sheet_name'])
    uom_dict = dict(zip(map_uom[mappings['MEINS']['map_key']], map_uom[mappings['MEINS']['map_value']]))
    sap_output['MEINS'] = df_filtered[mappings['MEINS']['source']].map(uom_dict).fillna('ERR')
    map_lgort = pd.read_excel(os.path.join(config['mapping_folder'], mappings['LGORT']['map_file']), sheet_name=mappings['LGORT']['sheet_name'])
    lgort_dict = dict(zip(map_lgort[mappings['LGORT']['map_key']], map_lgort[mappings['LGORT']['map_value']]))
    sap_output['LGORT'] = df_filtered[mappings['LGORT']['source']].map(lgort_dict).fillna('ERR')

    # 5. Template: forceer kolomvolgorde en -namen op basis van rij 5 (header=4)
    template_path = os.path.join('data', 'templates', 'Opdracht_template_MATMAS.xlsx')
    template_df = pd.read_excel(template_path, header=4)
    template_columns = template_df.columns.tolist()
    sap_output = sap_output.reindex(columns=template_columns)

    return sap_output