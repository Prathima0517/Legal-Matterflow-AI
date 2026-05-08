import json
from typing import Dict, Any , Optional, List
from pathlib import Path
from utils.azure_openai_client import AzureOpenAIClientSingleton
from utils.prompt_manager import prompt_manager  # Import the prompt manager


def get_field_descriptions(template_type: Optional[str] = None) -> List[str]:

    try:
        # Load template configuration
        config_path = Path(__file__).parent.parent / 'static' / 'template_config.json'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"Loaded template configuration from: {config_path}")
        
        template_path = None
        template_used = None

        if template_type:
            templates = config.get('templates', [])
            for template in templates:
                if template['name'] == template_type:
                    template_path = template['path']
                    template_used = template_type
                    print(f"Found requested template: {template_type}")
                    break

        if not template_path:
            default_template = config.get('default_template', {})
            if default_template:
                template_path = default_template['path']
                template_used = default_template['name']
                if template_type:
                    print(f"Template '{template_type}' not found, falling back to default: {template_used}")
                else:
                    print(f"No template specified, using default: {template_used}")
            else:
                print("Error: No default template found in configuration")
                return []
        
        # Construct full path
        full_template_path = Path(__file__).parent.parent / template_path
        
        # Check if template file exists
        if not full_template_path.exists():
            print(f"Error: Template file not found at {full_template_path}")
            return []
        
        # Load template and extract fields
        with open(full_template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        fields = template.get('fields', [])
        field_descriptions = [
            f"{field['field_name']} ({field.get('field_type', 'Text')}): {field.get('field_notes', '')} Sample: {field.get('sample_data', '')}"
            for field in fields
        ]
        
        print(f"Successfully loaded {field_descriptions} fields from template: {template_used}")
        print(f"Template file path: {full_template_path}")
        
        return field_descriptions
        
    except FileNotFoundError as e:
        print(f"Error: Configuration file not found - {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return []
    except KeyError as e:
        print(f"Error: Missing key in configuration - {e}")
        return []
    except Exception as e:
        print(f"Error reading template configuration: {e}")
        return []

def extract_entities(text: str, template_type: str) -> Dict[str, Any]:
    try:
        azure_client_singleton = AzureOpenAIClientSingleton()
        client = azure_client_singleton.get_client()
        deployment_name = azure_client_singleton.get_deployment_name()
        

        field_descriptions = get_field_descriptions(template_type);
        
        if not field_descriptions:
            return {
                "extracted_text": text,
                "entities": [],
                "error": "Failed to load field descriptions from template"
            }
        
        prompt = prompt_manager.get_entity_extraction_prompt(field_descriptions, text)

        print("Azure OpenAI with the following prompt to field extraction:")
        print(prompt)

        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            top_p=1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        print(f"Raw AI model response: {repr(content)}")
        if not content:
            return {
                "entities": [],
                "error": "Empty response from Azure OpenAI"
            }
        
        try:
            parsed_json = json.loads(content)
            # Handle both list and dict outputs
            if isinstance(parsed_json, list):
                entities = parsed_json
            elif isinstance(parsed_json, dict):
                # If the dict has a 'result' key and its value is a list, flatten it
                if 'result' in parsed_json and isinstance(parsed_json['result'], list):
                    entities = parsed_json['result']
                else:
                    entities = [
                        {"field": key, "value": value}
                        for key, value in parsed_json.items()
                    ]
            else:
                entities = []
            
            # Calculate overall accuracy percentage
            def confidence_score(conf):
                if conf == "high":
                    return 1.0
                elif conf == "medium":
                    return 0.7
                elif conf == "low":
                    return 0.3
                return 0.0
            if entities and isinstance(entities, list):
                scores = [confidence_score(e.get("confidence", "low")) for e in entities]
                overall_accuracy = int((sum(scores) / len(scores)) * 100) if scores else 0
            else:
                overall_accuracy = 0
            return {
                "overall_accuracy": overall_accuracy,
                "entities": entities
            }
            
        except json.JSONDecodeError as json_err:
            print(f"JSON parse error: {json_err}")
            return {
                "entities": [],
                "error": f"Failed to parse JSON response: {str(json_err)}"
            }
    
    except Exception as e:
        print(f"Azure OpenAI Exception: {e}")
        return {
            "entities": [],
            "error": f"AI extraction failed: {str(e)}"
        }
