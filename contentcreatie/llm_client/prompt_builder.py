import os
import json
import inspect
import types
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from jinja2.meta import find_undeclared_variables
from typing import Dict, Any, List, Optional, Set

from jsonschema import ValidationError, validate, exceptions

class PromptBuilder:
    """
    Loads templates and an optional JSON schema to create a method with a
    dynamic signature for building prompt message lists.
    """

    def __init__(self, template_path: str, name: str):
        """
        Initializes the processor by loading templates and the corresponding schema.

        :param template_path: str, The file system path to the templates directory.
        :param name: str, The base name for template files (e.g., 'search').
        """
        self.name = name
        self.template_path = template_path
        
        self.env = Environment(loader=FileSystemLoader(self.template_path))
        
        self.schema: Optional[Dict[str, Any]] = None
        self.schema_str: str = ""
        self.user_template: Optional[Template] = None
        self.system_template: Optional[Template] = None
        self.user_vars: Set[str] = set()
        self.system_vars: Set[str] = set()
        
        self.load_templates()

    def load_templates(self):
        """
        Loads templates and schema, parsing variables correctly.

        This method ensures that at least one template (user or system) is
        loaded. The JSON schema is optional.

        :raises FileNotFoundError: If neither {self.name}.j2 (user) nor
                                  {self.name}_system.j2 (system) can be found
                                  in the template path.
        """

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
            self.user_template = self.env.from_string(user_source)
            user_ast = self.env.parse(user_source)
            self.user_vars = find_undeclared_variables(user_ast)
        except TemplateNotFound:
            self.user_template = None
            self.user_vars = set()

        try:
            system_source = self.env.loader.get_source(self.env, f"{self.name}_system.j2")[0]
            self.system_template = self.env.from_string(system_source)
            system_ast = self.env.parse(system_source)
            self.system_vars = find_undeclared_variables(system_ast)
        except TemplateNotFound:
            self.system_template = None
            self.system_vars = set()
            
        if self.user_template is None and self.system_template is None:
            raise FileNotFoundError(
                f"No templates found for '{self.name}'. At least one of "
                f"'{self.name}.j2' or '{self.name}_system.j2' must exist "
                f"in {self.template_path}"
            )
        
        self._replace_create_prompt_method(self.user_vars, self.system_vars)

    def _replace_create_prompt_method(self, user_vars: Set, system_vars: Set):
        """
        Builds and assigns a new 'create_prompt' method that handles chat history.

        :param user_vars: Set, A set of variable names found in the user template.
        :param system_vars: Set, A set of variable names found in the system template.
        """
        all_prompt_vars = (user_vars | system_vars) - {'json_schema'}

        params = [
            inspect.Parameter('history', inspect.Parameter.KEYWORD_ONLY, default=None)
        ]
        params.extend([
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=inspect.Parameter.empty)
            for name in sorted(list(all_prompt_vars))
        ])
        signature = inspect.Signature(params)

        def dynamic_create_prompt(instance_self: "PromptBuilder", *args, **kwargs) -> List[Dict[str, str]]:
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments
            
            history = all_args.pop('history', None)
            messages = history[:] if history else []

            # --- System Message Handling ---
            rendered_system = None
            if instance_self.system_template:
                system_data = {k: v for k, v in all_args.items() if k in instance_self.system_vars}
                rendered_system = instance_self.system_template.render(
                    json_schema=instance_self.schema_str, **system_data
                )

            # Remove any existing system messages
            messages = [msg for msg in messages if msg.get('role') != 'system']

            # Insert the updated system message if it was rendered
            if rendered_system:
                messages.insert(0, {"role": "system", "content": rendered_system})

            # --- User Message Handling ---
            rendered_user = None
            if instance_self.user_template:
                user_data = {k: v for k, v in all_args.items() if k in instance_self.user_vars}
                rendered_user = instance_self.user_template.render(
                    json_schema=instance_self.schema_str, **user_data
                )
            
            # If we rendered a user message, append it (unless it's a duplicate)
            if rendered_user:
                if not (history and history[-1].get("role") == "user" and history[-1].get("content") == rendered_user):
                    messages.append({"role": "user", "content": rendered_user})

            return messages

        dynamic_create_prompt.__signature__ = signature
        dynamic_create_prompt.__doc__ = (
            "Dynamically generated prompt creation method.\n\n"
            "Renders system and/or user prompts using provided keyword arguments.\n\n"
            ":param history: Optional[List[Dict[str, str]]], A list of previous messages, defaults to None\n"
            ":param **kwargs: Keyword arguments matching variables in the templates.\n"
            ":return: List[Dict[str, str]], The fully constructed list of messages."
        )
        self.create_prompt = types.MethodType(dynamic_create_prompt, self)

    def verify_json(self, json_data: dict) -> bool:
        """
        Verifies if the provided JSON data conforms to the loaded JSON schema.

        :param json_data: dict, The JSON data (as a dict) to validate.
        :return: bool, True if the data is valid or if no schema is loaded, False otherwise.
        """
        if self.schema is None:
            # If no schema is defined, any JSON is considered "valid"
            return True
        try:
            validate(instance=json_data, schema=self.schema)
            return True
        except (ValidationError, exceptions.SchemaError):
            return False

    def create_prompt(self, *, history: Optional[List[Dict[str, str]]] = None, **kwargs) -> List[Dict[str, str]]:
        """
        Placeholder for the dynamically generated method.
        
        This method is overwritten by `_replace_create_prompt_method` upon
        initialization. Its signature will be dynamically generated based on
        the variables found in the loaded Jinja2 templates.
        
        :param history: Optional[List[Dict[str, str]]], A list of previous messages, defaults to None
        :param **kwargs: Keyword arguments matching variables in the templates.
        :return: List[Dict[str, str]], The fully constructed list of messages.
        :raises TypeError: If required template variables are missing from kwargs.
        """
        # This code path should not be reachable if __init__ succeeds.
        raise NotImplementedError(
            "PromptBuilder was not initialized correctly. "
            "The 'create_prompt' method was not dynamically replaced."
        )