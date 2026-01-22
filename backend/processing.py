import pandas as pd
from datetime import datetime
from pathlib import Path
import warnings
from typing import Optional, Dict, Any, List

# Internal imports
from .configuration import ConfigManager
from .mappings import MappingService

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

class SAPDataConverter:
    """Core logic for converting Legacy Hospital Data to SAP format."""

    def __init__(self, settings_file: str = 'settings.json'):
        self.cfg_loader = ConfigManager(settings_file)
        self.settings = self.cfg_loader.load_settings()
        self.mapper = MappingService(self.settings.get('mapping_folder', 'data/mappings'))

    def _get_site_code(self, filepath: Path) -> str:
        """Parses site code (WERKS) from filename, default to ZH01."""
        try:
            return filepath.stem.split('_')[-1]
        except:
            return "ZH01"

    def _load_raw_data(self, filepath: Path) -> pd.DataFrame:
        """Loads and merges Articles and Location data from Input."""
        try:
            # Try Excel first
            df_art = pd.read_excel(filepath, sheet_name='Artikels', dtype=str)
            df_loc = pd.read_excel(filepath, sheet_name='Locatie', dtype=str)
        except:
            # Fallback to CSV strategy
            try:
                folder = filepath.parent
                df_art = pd.read_csv(folder / 'Artikels.csv', dtype=str)
                df_loc = pd.read_csv(folder / 'Locatie.csv', dtype=str)
            except:
                return pd.DataFrame()

        # Data Cleaning
        for d in [df_art, df_loc]:
            d.columns = d.columns.str.strip()
            str_cols = d.select_dtypes(include='object').columns
            d[str_cols] = d[str_cols].apply(lambda x: x.str.strip())

        # Join
        return pd.merge(df_loc, df_art, on='ArtikelNr', how='left')

    def _filter_active_records(self, df: pd.DataFrame, reference_date: datetime) -> pd.DataFrame:
        """Filters active records based on 'Actief' flag and EndDate."""
        df['EindDat_Check'] = pd.to_datetime(df['EindDat'], errors='coerce')
        
        mask_active = df['Actief'] == 'J'
        mask_date = (df['EindDat_Check'].isna()) | (df['EindDat_Check'] >= reference_date)
        
        return df[mask_active & mask_date].copy().reset_index(drop=True)

    def _process_fields(self, df_source: pd.DataFrame, site_code: str) -> pd.DataFrame:
        """Applies configuration rules to generate SAP fields."""
        df_target = pd.DataFrame()
        field_rules: Dict[str, Any] = self.settings.get('mappings', {})

        for target_col, rule in field_rules.items():
            r_type = rule.get('type')
            
            try:
                if r_type == 'filename_extraction':
                    df_target[target_col] = site_code
                
                elif r_type == 'direct':
                    df_target[target_col] = df_source[rule['source']]
                
                elif r_type == 'map':
                    self._apply_mapping_rule(df_source, df_target, target_col, rule)

                elif r_type == 'logic_length':
                    self._apply_length_logic(df_source, df_target, target_col, rule)
            
            except Exception:
                df_target[target_col] = "ERROR"

        return df_target

    def _apply_mapping_rule(self, source_df, target_df, target_col, rule):
        src_col = rule['source']
        map_dict = {}
        
        if 'map_file' in rule:
            map_dict = self.mapper.get_mapping_dict(
                rule['map_file'], 
                rule.get('sheet_name', 0),
                rule.get('map_key'), 
                rule.get('map_value')
            )

        # Lookup
        source_values = source_df[src_col].fillna('').astype(str).str.strip().str.upper()
        mapped_values = source_values.map(map_dict)
        
        # Fallback handling
        strategy = rule.get('fallback_strategy', 'error')
        if strategy == 'source_value':
            target_df[target_col] = mapped_values.fillna(source_df[src_col])
        elif strategy == 'default_value':
            target_df[target_col] = mapped_values.fillna(rule.get('default_value', ''))
        else:
            target_df[target_col] = mapped_values.fillna('ERR')

    def _apply_length_logic(self, source_df, target_df, target_col, rule):
        src_col = rule['source']
        limit = rule.get('max_length', 40)
        fallback = rule.get('fallback_strategy', 'truncate')
        
        map_dict = {}
        if 'map_file' in rule:
            map_dict = self.mapper.get_mapping_dict(
                rule['map_file'], 
                rule.get('sheet_name', 0),
                rule.get('map_key'), 
                rule['map_value']
            )

        def transform(val):
            s_val = str(val).strip() if pd.notnull(val) else ""
            if len(s_val) > limit:
                # Check mapping
                if s_val.upper() in map_dict:
                    return map_dict[s_val.upper()]
                # Truncate if allowed
                if fallback == 'truncate':
                    return s_val[:limit]
            return s_val

        target_df[target_col] = source_df[src_col].apply(transform)

    def _run_calculations(self, source_df, target_df):
        """Executes custom row-level calculations."""
        calcs = self.settings.get('custom_calculations', [])
        for c in calcs:
            try:
                target_df[c['target_column']] = source_df.apply(
                    lambda row: eval(c['formula'], {}, {'row': row}), axis=1
                )
            except:
                pass
        return target_df

    def _enforce_template(self, df_target: pd.DataFrame, site_code: str) -> pd.DataFrame:
        """Aligns output with the official template."""
        print("📝 Standardizing output to template...")
        tpl_path = self.settings.get('template_file', 'data/templates/Opdracht_template_MATMAS.xlsx')
        
        try:
            # We don't crash if template missing, just skip or fail safely as before
            tpl_df = pd.read_excel(tpl_path, header=4)
            # Filter string headers
            valid_cols = [c.strip() for c in tpl_df.columns if isinstance(c, str)]
            
            # Reindex adds missing columns and removes extras
            df_final = df_target.reindex(columns=valid_cols).fillna("")
            
            # Special Rule: Force WERKS
            if 'WERKS' in df_final.columns:
                df_final['WERKS'] = site_code
                print(f"✅ WERKS constrained to: {site_code}")
                
            return df_final
            
        except Exception as e:
            print(f"❌ Template Error: {e}")
            return df_target

    def run(self, input_file: str, date_override: Optional[str] = None) -> pd.DataFrame:
        """Main execution method."""
        print("🚀 Start slimme conversie (Refactored Core)...")
        path_obj = Path(input_file)
        
        # Date Logic
        ref_date = pd.to_datetime(date_override) if date_override else datetime.now()
        
        # Site ID
        site_id = self._get_site_code(path_obj)
        
        # 1. Ingestion
        merged_data = self._load_raw_data(path_obj)
        if merged_data.empty:
             return pd.DataFrame()

        # 2. Filtering
        clean_data = self._filter_active_records(merged_data, ref_date)
        if clean_data.empty:
            return pd.DataFrame()

        # 3. Field Processing
        sap_data = self._process_fields(clean_data, site_id)

        # 4. Calculations
        sap_data = self._run_calculations(clean_data, sap_data)

        # 5. Template Formatting
        final_data = self._enforce_template(sap_data, site_id)

        return final_data
