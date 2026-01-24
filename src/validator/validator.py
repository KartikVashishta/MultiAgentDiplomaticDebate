import re
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

class ProfileValidator:
    """A validator class for ensuring the quality and consistency of country profiles.

    This class uses LLM to validate and potentially modify country profile data,
    ensuring accuracy, consistency, and completeness of the information.

    Attributes:
        llm (ChatOpenAI): LLM instance for validation operations

    Examples:
        >>> validator = ProfileValidator(model_name="gpt-4o-mini", temperature=0.2)
        >>> updated_profile, changes = validator.validate(
        ...     model=country_profile,
        ...     prompt_template=PROFILE_VALIDATOR_PROMPT,
        ...     is_debug=True
        ... )
        >>> print(f"Made {len(changes)} changes to the profile")
    """

    def __init__(self, model_name: str, temperature: float = 0.5, max_tokens: int = 8000):
        """Initialize the profile validator.

        Args:
            model_name (str): Name of the LLM model to use
            temperature (float, optional): Temperature for LLM responses. Defaults to 0.5
            max_tokens (int, optional): Maximum tokens in LLM response. Defaults to 8000
        """
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
    def _parse_changes(self, validation_response: str) -> List[Dict[str, str]]:
        """Parse the LLM validation response into structured changes.

        Extracts change instructions from the LLM response, including the type
        of change (ADD/REPLACE/REMOVE/UPDATE/CORRECT/CONTEXT), the field to
        modify, and the reason for the change.

        Args:
            validation_response (str): Raw response from the LLM validator

        Returns:
            List[Dict[str, str]]: List of changes, each containing:
                - type: Type of change to make
                - field_path: Path to the field in the model
                - new_value: New value to apply
                - reason: Explanation for the change
        """
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
        """Apply the parsed changes to the Pydantic model.

        Modifies the model according to the specified changes, handling special
        cases like GDP formatting and list modifications.

        Args:
            model (BaseModel): Original Pydantic model to modify
            changes (List[Dict[str, str]]): List of changes from _parse_changes

        Returns:
            BaseModel: Updated model with all changes applied

        Note:
            - Special handling for economic_profile.gdp field
            - Supports nested field paths using dot notation
            - Preserves model validation through Pydantic
        """
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
