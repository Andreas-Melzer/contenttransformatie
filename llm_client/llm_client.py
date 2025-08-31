import os
import json
import openai
import dotenv
import sys
from typing import Callable, Optional, Dict, Any, List, Union
from openai.types.chat import ChatCompletion

from json_extractor import JsonExtractor
from config.settings import Settings
settings = Settings()


def json_post_process(raw_output: str) -> Any:
    """Parses raw string output as JSON, handling markdown code blocks.

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
    obj = JsonExtractor.extract_valid_json(raw_output)
    return obj

class _BaseClient:
    """A base class to handle shared API client initialization."""
    def __init__(self):
        """Initializes clients based on the global settings object."""
        self.clients: Dict[str, openai.OpenAI] = {}
        for name, client_config in settings.clients.items():
            if name.startswith("azure"):
                if client_config.api_key and client_config.azure_endpoint:
                    self.clients[name] = openai.AzureOpenAI(
                        api_key=client_config.api_key,
                        api_version=client_config.api_version,
                        azure_endpoint=client_config.azure_endpoint
                    )
                else:
                    print(f"Warning: Missing API key or endpoint for '{name}'. Client disabled.", file=sys.stderr)
            elif name == "openrouter":
                if client_config.api_key:
                    self.clients[name] = openai.OpenAI(
                        base_url=client_config.base_url,
                        api_key=client_config.api_key
                    )
                else:
                    print(f"Warning: Missing API key for '{name}'. Client disabled.", file=sys.stderr)
            elif name == "local":
                 self.clients[name] = openai.OpenAI(
                    base_url=client_config.base_url,
                    api_key=client_config.api_key
                )


    def _get_client(self, client_name: str) -> openai.OpenAI:
        """Retrieves an initialized OpenAI client by name.

        :param client_name: str, The name of the client to retrieve.
        :raises ValueError: If the client name is not found.
        :return: openai.OpenAI, The requested OpenAI client instance.
        """
        client = self.clients.get(client_name)
        if not client:
            raise ValueError(f"Client '{client_name}' not found or not configured. Available clients: {list(self.clients.keys())}")
        return client

class LLMResult:
    """A smart wrapper for OpenAI ChatCompletion responses that auto-processes content."""
    def __init__(self, response: ChatCompletion, processor: Optional[Callable[[str], Any]] = None):
        """Initializes the result object.

        :param response: ChatCompletion, The ChatCompletion object from the openai client.
        :param processor: Optional[Callable[[str], Any]], An optional callable to apply to the raw content, defaults to None.
        :return: None,
        """
        self.api_response = response
        self._processor = processor

    @property
    def message(self):
        """Gets the primary message object from the response.

        :return: openai.types.chat.chat_completion_message.ChatCompletionMessage, The first message object from the response choices.
        """
        return self.api_response.choices[0].message

    @property
    def raw_content(self) -> Optional[str]:
        """Gets the original, unprocessed string content from the response.

        :return: Optional[str], The raw string content of the message.
        """
        return self.message.content

    @property
    def content(self) -> Any:
        """Gets the processed content, applying a processor if available.

        :return: Any, The processed content, or raw content if no processor is set.
        """
        if self._processor and self.raw_content is not None:
            return self._processor(self.raw_content)
        return self.raw_content

    @property
    def thinking(self) -> Optional[List[Dict[str, Any]]]:
        """Extracts tool calls made by the model, if any.

        :return: Optional[List[Dict[str, Any]]], A list of tool calls or None if there are none.
        """
        if not self.message.tool_calls:
            return None
        return [
            {
                "id": tool.id,
                "type": tool.type,
                "function": {"name": tool.function.name, "arguments": tool.function.arguments},
            }
            for tool in self.message.tool_calls
        ]

    @property
    def usage(self) -> Dict[str, int]:
        """Gets token usage statistics for the request.

        :return: Dict[str, int], A dictionary with token usage stats.
        """
        return dict(self.api_response.usage) if self.api_response.usage else {}

REASONING_MODELS = [
 "gpt-5-mini",
 "gpt-5"   
]
class LLMProcessor(_BaseClient):
    """A client for making Chat Completion API requests and returning structured results."""
    def __init__(
        self,
        model: str = settings.llm_model,
        system_prompt: Optional[str] = None,
        default_post_process: Optional[Callable[[str], Any]] = None,
        temperature=1,
        **kwargs
    ):
        """Initializes the LLMProcessor.

        :param model: str, The default model to use for completions, defaults to 'LLM'.
        :param client_name: str, The default client to use ('local' or 'openrouter'), defaults to 'local'.
        :param system_prompt: Optional[str], An optional default system prompt, defaults to None.
        :param default_post_process: Optional[Callable[[str], Any]], A default processor for all results, defaults to None.
        :param kwargs: Any, Additional keyword arguments passed to the _BaseClient.
        :return: None,
        """
        super().__init__(**kwargs)
        self.model = model
        self.client_name = settings.llm_client_map.get(model)
        if not self.client_name:
            raise ValueError(f"Model '{model}' not found in llm_client_map in settings.")
        self.system_prompt = system_prompt
        self.default_post_process = default_post_process
        self._client = self._get_client(self.client_name)
        self.temperature = temperature

    def process(
        self,
        messages: List[Dict[str, Any]],
        post_process: Optional[Callable[[str], Any]] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort : Optional[str] = "low",
        **kwargs: Any
    ) -> LLMResult:
        """Sends a request to the model and returns a wrapped LLMResult.

        :param messages: List[Dict[str, Any]], A list of messages conforming to the OpenAI API structure.
        :param post_process: Optional[Callable[[str], Any]], A processor for this response, overriding the instance default, defaults to None.
        :param max_completion_tokens: Optional[int], The maximum number of tokens to generate, defaults to None.
        :param reasoning_effort: Optional[str] any of "minimal","low","medium","high"
        :param kwargs: Any, Other OpenAI chat completion parameters (e.g., temperature).
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

class EmbeddingProcessor(_BaseClient):
    """A client for generating embeddings from various providers."""
    def __init__(
        self,
        embedding_model: str = settings.embedding_model,
        **kwargs: Any
    ):
        """Initializes the EmbeddingProcessor.

        :param embedding_model: str, The default embedding model to use, defaults to "text-embedding-3-small".
        :param client_name: str, The client to use ('azure', 'openrouter', 'local'), defaults to 'azure'.
        :param kwargs: Any, Additional keyword arguments passed to the _BaseClient.
        :return: None,
        """
        super().__init__(**kwargs)
        self.embedding_model = embedding_model
        self.client_name = settings.embedding_client_map.get(embedding_model)
        if not self.client_name:
            raise ValueError(f"Embedding model '{embedding_model}' not found in embedding_client_map in settings.")
        self._client = self._get_client(self.client_name)

    def embed(
        self,
        texts: Union[str, List[str]],
        **kwargs: Any
    ) -> Union[List[float], List[List[float]]]:
        """Generates embeddings for the given text(s).

        :param texts: Union[str, List[str]], A single string or a list of strings to embed.
        :param kwargs: Any, Other OpenAI embedding parameters (e.g., dimensions).
        :return: Union[List[float], List[List[float]]], A single embedding vector if the input was a string, or a list of vectors if the input was a list of strings.
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

        if is_single_string:
            return embeddings[0]
        else:
            return embeddings