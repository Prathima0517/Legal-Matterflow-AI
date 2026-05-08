from pathlib import Path


class PromptManager:
    
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent / 'static' / 'prompts'
        self._template_cache = {}
    
    def load_template(self, template_path: str) -> str:
        if template_path in self._template_cache:
            return self._template_cache[template_path]

        clean_path = template_path.strip().replace('../', '').replace('..', '').lstrip('/')
        full_path = self.prompts_dir / clean_path
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self._template_cache[template_path] = content
                return content
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found: {full_path}")
        except Exception as e:
            raise Exception(f"Error loading prompt template {template_path}: {e}")
    
    def get_classification_prompt(self, templates: list, text: str) -> str:
        max_chars = 6000
        if len(text) > max_chars:
            text = text[:max_chars] + "... [truncated]"

        templates_list = "\n".join([f"- {template}" for template in templates])
        template_content = self.load_template("/template_classification.txt")
        
        return template_content.format(
            templates=templates_list,
            document=text
        )
    
    def get_entity_extraction_prompt(self, field_descriptions: list, text: str) -> str:
        field_descriptions_str = "\n".join(field_descriptions)
        template_content = self.load_template("/entity_extraction.txt")
        
        return template_content.format(
            field_descriptions=field_descriptions_str,
            document=text
        )


prompt_manager = PromptManager()
