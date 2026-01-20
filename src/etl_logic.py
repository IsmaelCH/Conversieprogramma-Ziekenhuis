import pandas as pd
import os
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

def load_config():
    if not os.path.exists('config.json'):
        raise FileNotFoundError("config.json niet gevonden!")
    with open('config.json', 'r') as f:
        return json.load(f)

def load_excel_mapping(filepath, sheet_name, key_col, val_col):
    if not os.path.exists(filepath):
        return {}
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name, dtype=str)
        df.columns = df.columns.str.strip()
        if key_col not in df.columns or val_col not in df.columns:
            return {}
        df[key_col] = df[key_col].fillna('').astype(str).str.strip().str.upper()
        df[val_col] = df[val_col].fillna('').astype(str).str.strip()
        df = df[df[key_col] != '']
        return dict(zip(df[key_col], df[val_col]))
    except:
        return {}

def run_conversion(source_file_path, peildatum=None):
    print("🚀 Start slimme conversie (Final Fix)...")
    config = load_config()
    if peildatum is None:
        peildatum = datetime.now()
    peildatum = pd.to_datetime(peildatum)
    filename = os.path.basename(source_file_path)
    try:
        base_name = os.path.splitext(filename)[0]
        vestiging_code = base_name.split('_')[-1]
    except:
        vestiging_code = "ZH01"
    try:
        df_art = pd.read_excel(source_file_path, sheet_name='Artikels', dtype=str)
        df_loc = pd.read_excel(source_file_path, sheet_name='Locatie', dtype=str)
    except:
        try:
            input_dir = os.path.dirname(source_file_path)
            df_art = pd.read_csv(os.path.join(input_dir, 'Artikels.csv'), dtype=str)
            df_loc = pd.read_csv(os.path.join(input_dir, 'Locatie.csv'), dtype=str)
        except:
            return pd.DataFrame()
    for df in [df_art, df_loc]:
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].str.strip()
    df_merged = pd.merge(df_loc, df_art, on='ArtikelNr', how='left')
    df_merged['EindDat_Check'] = pd.to_datetime(df_merged['EindDat'], errors='coerce')
    cond = (
        (df_merged['Actief'] == 'J') & 
        ((df_merged['EindDat_Check'].isna()) | (df_merged['EindDat_Check'] >= peildatum))
    )
    df_filtered = df_merged[cond].copy().reset_index(drop=True)
    if df_filtered.empty:
        return pd.DataFrame()
    sap_output = pd.DataFrame()
    mapping_cache = {}
    for sap_field, rules in config['mappings'].items():
        mapping_dict = {}
        if 'map_file' in rules:
            fname = rules['map_file']
            sheet = rules.get('sheet_name', 0)
            cache_key = f"{fname}_{sheet}"
            if cache_key not in mapping_cache:
                path = os.path.join(config['mapping_folder'], fname)
                mapping_cache[cache_key] = load_excel_mapping(path, sheet, rules['map_key'], rules['map_value'])
            mapping_dict = mapping_cache[cache_key]
        try:
            if rules['type'] == 'filename_extraction':
                sap_output[sap_field] = vestiging_code
            elif rules['type'] == 'direct':
                sap_output[sap_field] = df_filtered[rules['source']]
            elif rules['type'] == 'map':
                col = rules['source']
                source_vals = df_filtered[col].fillna('').astype(str).str.strip().str.upper()
                mapped = source_vals.map(mapping_dict)
                fallback = rules.get('fallback_strategy', 'error')
                if fallback == 'source_value':
                    sap_output[sap_field] = mapped.fillna(df_filtered[col])
                elif fallback == 'default_value':
                    sap_output[sap_field] = mapped.fillna(rules.get('default_value', ''))
                else:
                    sap_output[sap_field] = mapped.fillna('ERR')
            elif rules['type'] == 'logic_length':
                col = rules['source']
                max_len = rules.get('max_length', 40)
                fallback = rules.get('fallback_strategy', 'truncate')
                def logic(val):
                    val = str(val).strip() if pd.notnull(val) else ""
                    if len(val) > max_len:
                        lookup = val.upper()
                        res = mapping_dict.get(lookup)
                        if res: return res
                        if fallback == 'truncate': return val[:max_len]
                    return val
                sap_output[sap_field] = df_filtered[col].apply(logic)
        except:
            sap_output[sap_field] = "ERROR"
    if 'custom_calculations' in config:
        for calc in config['custom_calculations']:
            try:
                sap_output[calc['target_column']] = df_filtered.apply(
                    lambda row: eval(calc['formula'], {}, {'row': row}), axis=1
                )
            except: pass
    print("📝 Template toepassen...")
    template_path = config.get('template_file', 'data/templates/Opdracht_template_MATMAS.xlsx')
    try:
        template_df = pd.read_excel(template_path, header=4)
        template_cols = [c.strip() for c in template_df.columns if isinstance(c, str)]
        sap_output = sap_output.reindex(columns=template_cols).fillna("")
        # --- DE OPLOSSING: HARD FORCE WERKS ---
        if 'WERKS' in sap_output.columns:
            sap_output['WERKS'] = vestiging_code
            print(f"✅ WERKS geforceerd op: {vestiging_code}")
    except Exception as e:
        print(f"❌ Template error: {e}")
    return sap_output