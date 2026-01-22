import json
from pathlib import Path

class ConfigManager:
    """Manages application settings loading."""
    
    def __init__(self, settings_path: str = 'settings.json'):
        self.settings_path = Path(settings_path)

    def load_settings(self) -> dict:
        """Loads the JSON configuration file."""
        if not self.settings_path.exists():
            raise FileNotFoundError(f"Settings file missing: {self.settings_path.absolute()}")
        
        with open(self.settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
