import re
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

class ProfileValidator:
    def __init__(self, model_name: str, temperature: float = 0.5, max_tokens: int = 8000):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
    def _parse_changes(self, validation_response: str) -> List[Dict[str, str]]:
        changes = []
    
        change_blocks = re.split(r'\n\s*\n', validation_response.strip())
        
        for block in change_blocks:
            if not block.strip():
                continue
        
            for change_type in ['ADD', 'REPLACE', 'REMOVE', 'UPDATE', 'CORRECT', 'CONTEXT']:
                pattern = rf'\[{change_type}\](.*?)\[{change_type}\]'
                content_match = re.search(pattern, block, re.DOTALL)
                if content_match:
                    content = content_match.group(1).strip()
                    reason_match = re.search(r'\[REASON\](.*?)\[REASON\]', block, re.DOTALL)
                    reason = reason_match.group(1).strip() if reason_match else "No reason provided"
                    
                    if ':' in content:
                        field_path, new_value = content.split(':', 1)
                        field_path = field_path.strip()
                        new_value = new_value.strip()
                        
                        changes.append({
                            'type': change_type,
                            'field_path': field_path,
                            'new_value': new_value,
                            'reason': reason
                        })
                    break  
        
        return changes

    def _apply_changes(self, model: BaseModel, changes: List[Dict[str, str]]) -> BaseModel:
        model_dict = model.model_dump()
        
        for change in changes:
            change_type = change['type']
            field_path = change['field_path']
            new_value = change['new_value']
            
            fields = field_path.split('.')
            current_dict = model_dict
            for i, field in enumerate(fields[:-1]):
                if field not in current_dict:
                    current_dict[field] = {}
                current_dict = current_dict[field]
            
            final_field = fields[-1]
            
            if field_path == 'economic_profile.gdp':
            
                import re
                
                year_match = re.search(r'in (\d{4})', new_value)
                if year_match:
                    current_dict['gdp_year'] = year_match.group(1)
                
                value_match = re.search(r'([\d.]+)\s*(trillion|billion|million)?\s*([A-Z]{3})', new_value)
                if value_match:
                    value = float(value_match.group(1))
                    unit = value_match.group(2) or "billion"
                    currency = value_match.group(3)
                    
                    if unit == "trillion":
                        value = value * 1000  
                    elif unit == "million":
                        value = value / 1000  

                    current_dict['gdp_unit'] = f"billion {currency}"
                    new_value = value

            
            if change_type == 'ADD':
                if isinstance(current_dict.get(final_field), list):
                    current_dict[final_field].append(new_value)
                else:
                    current_dict[final_field] = new_value
            elif change_type == 'REPLACE':
                current_dict[final_field] = new_value
            elif change_type == 'REMOVE':
                if isinstance(current_dict.get(final_field), list):
                    current_dict[final_field] = [
                        item for item in current_dict[final_field]
                        if item != new_value
                    ]
                else:
                    current_dict.pop(final_field, None)
            elif change_type in ['UPDATE', 'CORRECT']:
                if isinstance(current_dict.get(final_field), list):
                    for i, item in enumerate(current_dict[final_field]):
                        if str(item) in new_value:
                            current_dict[final_field][i] = new_value
                else:
                    current_dict[final_field] = new_value
        
        return model.__class__(**model_dict)

    def validate(
        self,
        model: BaseModel,
        prompt_template: Any,
        context: Optional[str] = None,
        is_debug: bool = False,
        overwrite: bool = False,
        save_path: Optional[str] = None
    ) -> Union[Tuple[BaseModel, List[Dict[str, str]]], str]:
        """
        Validates a Pydantic model using the provided prompt template.
        
        Args:
            model: The Pydantic model to validate
            prompt_template: The prompt template to use for validation
            context: Optional context to include in the prompt
            is_debug: If True, returns tuple of (updated_model, changes)
            overwrite: If True and is_debug is True, saves the updated model to save_path
            save_path: Optional path to save the validated model to
            
        Returns:
            If is_debug is False: The validation response string
            If is_debug is True: Tuple of (updated_model, list of changes)
        """
        prompt_vars = {
            "profile_data": model.model_dump_json(indent=2)
        }
        if context:
            prompt_vars["context"] = context
            
        validation_chain = prompt_template | self.llm
        validation_response = validation_chain.invoke(prompt_vars).content
        
        if not is_debug:
            return validation_response
            
        changes = self._parse_changes(validation_response)
        updated_model = self._apply_changes(model, changes)
        
        if is_debug and overwrite and save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(updated_model.model_dump_json(indent=2))
            print(f"[INFO] Saved validated profile to {save_path}")
        
        return updated_model, changes
