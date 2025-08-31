import os
import json
import inspect
import types
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from jinja2.meta import find_undeclared_variables
from typing import Dict, Any, List, Optional, Set

from jsonschema import ValidationError, validate, exceptions

class PromptBuilder:
    """Loads templates and a JSON schema to create a method with a dynamic signature."""

    def __init__(self, template_path: str, name: str):
        """Initializes the processor by loading templates and the corresponding schema."""
        self.name = name
        self.template_path = template_path
        
        self.env = Environment(loader=FileSystemLoader(self.template_path))
        self.load_templates()
    
    def load_templates(self):
        """Loads templates and schema, applying defaults and parsing variables correctly."""
        # --- Schema Loading ---
        schema_path = os.path.join(self.template_path, f"{self.name}.json")
        try:
            with open(schema_path, 'r') as f:
                self.schema = json.load(f)
            self.schema_str = json.dumps(self.schema, indent=2)
        except FileNotFoundError:
            self.schema = None
            self.schema_str = ""

        try:
            user_source = self.env.loader.get_source(self.env, f"{self.name}.j2")[0]
        except TemplateNotFound:
            user_source = "{{ query }}"
        
        self.user_template = self.env.from_string(user_source)
        user_ast = self.env.parse(user_source)
        self.user_vars = find_undeclared_variables(user_ast)

        try:
            system_source = self.env.loader.get_source(self.env, f"{self.name}_system.j2")[0]
            self.system_template = self.env.from_string(system_source)
            system_ast = self.env.parse(system_source)
            self.system_vars = find_undeclared_variables(system_ast)
        except TemplateNotFound:
            self.system_template = None
            self.system_vars = set()
        
        self._replace_create_prompt_method(self.user_vars, self.system_vars)

    # The flawed _get_template_vars has been removed.

    def _replace_create_prompt_method(self, user_vars: Set, system_vars: Set):
        """Builds and assigns a new 'create_prompt' method that handles chat history."""
        all_prompt_vars = (user_vars | system_vars) - {'json_schema'}

        params = [
            inspect.Parameter('history', inspect.Parameter.KEYWORD_ONLY, default=None)
        ]
        params.extend([
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=inspect.Parameter.empty)
            for name in sorted(list(all_prompt_vars))
        ])
        signature = inspect.Signature(params)

        def dynamic_create_prompt(instance_self, *args, **kwargs) -> List[Dict[str, str]]:
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments
            
            history = all_args.pop('history', None)
            messages = history[:] if history else []
            has_system_message = any(msg.get('role') == 'system' for msg in messages)

            if not has_system_message:
                system_data = {k: v for k, v in all_args.items() if k in system_vars}
                if instance_self.system_template:
                    rendered_system = instance_self.system_template.render(json_schema=instance_self.schema_str, **system_data)
                    messages.insert(0, {"role": "system", "content": rendered_system})
                else:
                    messages.insert(0, {"role": "system", "content": "You are an helpfull assisten"})

            user_data = {k: v for k, v in all_args.items() if k in user_vars}
            rendered_user = instance_self.user_template.render(json_schema=instance_self.schema_str, **user_data)
            
            # If the history passed in already contains this exact user message as the last item, don't add it again.
            if not (history and history[-1].get("role") == "user" and history[-1].get("content") == rendered_user):
                messages.append({"role": "user", "content": rendered_user})

            return messages

        dynamic_create_prompt.__signature__ = signature
        dynamic_create_prompt.__doc__ = "Dynamically generated prompt creation method."
        self.create_prompt = types.MethodType(dynamic_create_prompt, self)

    def verify_json(self, json_data: dict) -> bool:
        """Verifies if the provided JSON data conforms to the loaded JSON schema."""
        if self.schema is None:
            return True
        try:
            validate(instance=json_data, schema=self.schema)
            return True
        except (ValidationError, exceptions.SchemaError):
            return False