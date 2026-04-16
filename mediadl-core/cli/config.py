import json
import os
from typing import Dict, Any

def load_config(config_path: str = "mediadl.config.json") -> Dict[str, Any]:
    """Loads config-based execution parameters."""
    if not os.path.exists(config_path):
        return {}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load config {config_path}: {e}")
        return {}

def resolve_cmd_args(args: Any, config: Dict[str, Any]):
    """Merges args with explicit configurations from mediadl.config.json."""
    c = config.get("defaults", {})
    if not getattr(args, "format", None) and "format" in c:
        args.format = c["format"]
    
    # We could also handle strict execution limits here
    return args
