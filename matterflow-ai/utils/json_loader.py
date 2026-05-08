import json
import os
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

def load_json(file_path: str) -> Dict[str, Any]:
    try:
        if not os.path.isabs(file_path):
            current_dir = Path(__file__).parent.parent
            file_path = current_dir / file_path
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON from: {file_path}")
            return data
            
    except FileNotFoundError:
        logger.error(f"JSON file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading {file_path}: {e}")
        raise

def load_legal_templates(templates_file: str = "static/templates_list.json") -> List[str]:
    try:
        data = load_json(templates_file)
        templates = data.get("legal_document_templates", [])
        
        if not templates:
            raise ValueError("No templates found in JSON file")
        return templates
        
    except Exception as e:
        logger.warning(f"Failed to load templates from JSON: {e}")

