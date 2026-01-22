import pandas as pd
from pathlib import Path
from typing import Dict

class MappingService:
    """Handles retrieval of mapping data from Excel files."""
    
    def __init__(self, base_folder: str):
        self.base_folder = Path(base_folder)
        self._memory_cache = {}

    def get_mapping_dict(self, filename: str, sheet: str, key_header: str, val_header: str) -> Dict[str, str]:
        """Reads a mapping sheet and returns a dictionary."""
        cache_key = (filename, sheet, key_header, val_header)
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        full_path = self.base_folder / filename
        if not full_path.exists():
            return {}

        try:
            # Read excel
            df = pd.read_excel(full_path, sheet_name=sheet, dtype=str)
            df.columns = df.columns.str.strip()
            
            if key_header not in df.columns or val_header not in df.columns:
                return {}

            # Normalize
            df[key_header] = df[key_header].fillna('').astype(str).str.strip().str.upper()
            df[val_header] = df[val_header].fillna('').astype(str).str.strip()
            
            # Filter empty keys
            df_valid = df[df[key_header] != '']
            
            result = dict(zip(df_valid[key_header], df_valid[val_header]))
            self._memory_cache[cache_key] = result
            return result
        except Exception:
            # Silent failure as per original behavior implies empty dict return on read fail
            return {}
