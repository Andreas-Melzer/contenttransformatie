import json
import openai
import sys
from typing import Callable, Optional, Dict, Any, List, Union
from openai.types.chat import ChatCompletion
from json_extractor import JsonExtractor

def json_post_process(raw_output: str) -> Any:
    """
    Parses raw string output as JSON, handling markdown code blocks.
    :param raw_output: str, The raw string output from the language model.
    :return: Any, A dictionary if parsing succeeds, the original input if not a string, or None on parsing failure.
    """
    if not isinstance(raw_output, str):
        return raw_output

    cleaned_output = raw_output.strip()
    if cleaned_output.startswith("```json"):
        cleaned_output = cleaned_output.removeprefix("```json").strip()
    if cleaned_output.endswith("```"):
        cleaned_output = cleaned_output.removesuffix("```").strip()

    try:
        return json.loads(cleaned_output)
    except json.JSONDecodeError:
        print("Warning: Failed to decode LLM output as JSON.", file=sys.stderr)
        return None

def json_decode(raw_output:str) -> Any:
    """
    Extracts a valid JSON object from a raw string.
    :param raw_output: str, The raw string that may contain a JSON object.
    :return: Any, The extracted JSON object or None if not found.
    """
    return JsonExtractor.extract_valid_json(raw_output)

CLIENT_FACTORY = {
    "azure": {
        "class": openai.AzureOpenAI,
        "required_keys": {"api_key", "azure_endpoint", "api_version"},
    },
    "openrouter": {
        "class": openai.OpenAI,
        "required_keys": {"api_key", "base_url"},
    },
    "local": {
        "class": openai.OpenAI,
        "required_keys": {"api_key", "base_url"},
    },
    # Add a default for standard openai if needed
    "openai": {
        "class": openai.OpenAI,
        "required_keys": {"api_key", "base_url"},
    },
}

class _BaseProcessor:
    """A base class to handle shared client creation logic."""

    def _create_client(self, client_config: Dict[str, Any]) -> openai.OpenAI:
        """
        Creates an OpenAI client from a configuration dictionary using a factory pattern.
        :param client_config: Dict[str, Any], Configuration containing a 'type' key and other credentials.
        :return: openai.OpenAI, An initialized OpenAI client.
        :raises ValueError: If the configuration is invalid or the type is unsupported.
        """
        client_type = client_config.get("type", "openai")

        factory_config = CLIENT_FACTORY.get(client_type)
        if not factory_config:
            raise ValueError(f"Unsupported client type: '{client_type}'. Supported: {list(CLIENT_FACTORY.keys())}")

        required_keys = factory_config["required_keys"]
        if not required_keys.issubset(client_config.keys()):
            missing_keys = required_keys - client_config.keys()
            raise ValueError(f"{client_type} config is missing required keys: {', '.join(missing_keys)}")

        constructor_args = {key: client_config[key] for key in required_keys}
        
        ClientClass = factory_config["class"]
        return ClientClass(**constructor_args)


class LLMResult:
    """A smart wrapper for OpenAI ChatCompletion responses that auto-processes content."""
    def __init__(self, response: ChatCompletion, processor: Optional[Callable[[str], Any]] = None):
        """
        Initializes the result object.
        :param response: ChatCompletion, The ChatCompletion object from the openai client.
        :param processor: Optional[Callable[[str], Any]], An optional callable to apply to the raw content, defaults to None.
        """
        self.api_response = response
        self._processor = processor

    @property
    def message(self) -> Dict[str, Any]:
        """Gets the primary message object from the response and converts it to a dictionary."""
        message = self.api_response.choices[0].message
        message_dict = {
            "role": message.role,
            "content": message.content,
        }
        if message.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tool.id,
                    "type": tool.type,
                    "function": {
                        "name": tool.function.name,
                        "arguments": tool.function.arguments
                    }
                } for tool in message.tool_calls
            ]
        return message_dict

    @property
    def raw_content(self) -> Optional[str]:
        """Gets the original, unprocessed string content from the response."""
        return self.api_response.choices[0].message.content

    @property
    def content(self) -> Any:
        """Gets the processed content, applying a processor if available."""
        if self._processor and self.raw_content is not None:
            return self._processor(self.raw_content)
        return self.raw_content

    @property
    def tool_calls(self) -> Optional[List[Dict[str, Any]]]:
        """Extracts tool calls made by the model, if any."""
        message = self.api_response.choices[0].message
        if not message.tool_calls:
            return None
        return [
            {
                "id": tool.id,
                "type": tool.type,
                "function": {"name": tool.function.name, "arguments": tool.function.arguments},
            }
            for tool in message.tool_calls
        ]

    @property
    def usage(self) -> Dict[str, int]:
            """Gets token usage statistics for the request."""
            return dict(self.api_response.usage) if self.api_response.usage else {}

REASONING_MODELS = ["gpt-5-mini", "gpt-5"]

class LLMProcessor(_BaseProcessor):
    """A client for making Chat Completion API requests and returning structured results."""
    def __init__(
        self,
        model: str,
        client_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        default_post_process: Optional[Callable[[str], Any]] = None,
        temperature: float = 1.0,
    ):
        """
        Initializes the LLMProcessor.
        :param model: str, The model name to use for completions.
        :param client_config: Dict[str, Any], The configuration for the OpenAI client.
        :param system_prompt: Optional[str], An optional default system prompt.
        :param default_post_process: Optional[Callable[[str], Any]], A default processor for all results.
        :param temperature: float, The sampling temperature to use.
        """
        self.model = model
        self.system_prompt = system_prompt
        self.default_post_process = default_post_process
        self.temperature = temperature
        self._client = self._create_client(client_config)

    def process(
        self,
        messages: List[Dict[str, Any]],
        post_process: Optional[Callable[[str], Any]] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = "low",
        **kwargs: Any
    ) -> LLMResult:
        """
        Sends a request to the model and returns a wrapped LLMResult.
        :param messages: List[Dict[str, Any]], A list of messages for the API.
        :param post_process: Optional[Callable[[str], Any]], A processor for this response.
        :param max_completion_tokens: Optional[int], The maximum number of tokens to generate.
        :param reasoning_effort: Optional[str], Reasoning effort for capable models.
        :return: LLMResult, An LLMResult object wrapping the API response.
        """
        processor_to_use = post_process if post_process is not None else self.default_post_process
        
        full_messages = messages[:]
        if self.system_prompt and not any(m['role'] == 'system' for m in full_messages):
            full_messages.insert(0, {"role": "system", "content": self.system_prompt})

        request_params = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": full_messages,
            **kwargs
        }
        
        if self.model in REASONING_MODELS:
            request_params['reasoning_effort'] = reasoning_effort
        if max_completion_tokens is not None:
            request_params["max_tokens"] = max_completion_tokens
    
        completion = self._client.chat.completions.create(**request_params)
        return LLMResult(response=completion, processor=processor_to_use)

class EmbeddingProcessor(_BaseProcessor):
    """A client for generating embeddings."""
    def __init__(
        self,
        embedding_model: str,
        client_config: Dict[str, Any],
    ):
        """
        Initializes the EmbeddingProcessor.
        :param embedding_model: str, The embedding model to use.
        :param client_config: Dict[str, Any], The configuration for the OpenAI client.
        """
        self.embedding_model = embedding_model
        self._client = self._create_client(client_config)

    def embed(
        self,
        texts: Union[str, List[str]],
        **kwargs: Any
    ) -> Union[List[float], List[List[float]]]:
        """
        Generates embeddings for the given text(s).
        :param texts: Union[str, List[str]], A single string or a list of strings to embed.
        :return: Union[List[float], List[List[float]]], An embedding vector or a list of vectors.
        """
        is_single_string = isinstance(texts, str)
        input_texts = [texts] if is_single_string else texts

        if not input_texts:
            return []

        response = self._client.embeddings.create(
            model=self.embedding_model,
            input=input_texts,
            **kwargs
        )

        embeddings = [item.embedding for item in response.data]
        return embeddings[0] if is_single_string else embeddings