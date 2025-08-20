import json
from typing import Optional, Dict, Any, List

from .llm_client import LLMProcessor
from .tools.tool_base import ToolBase
from .prompt_builder import PromptBuilder

class MultiTurnAgent:
    def __init__(
        self,
        llm_processor: LLMProcessor,
        prompt_processor: PromptBuilder,
        tools: Optional[List[ToolBase]] = None,
        max_history_turns: int = 5
    ):
        """Initializes the agent with an internal, stateful scratchpad."""
        self.llm_processor = llm_processor
        self.prompt_processor = prompt_processor
        self.max_history_turns = max_history_turns
        self.messages: List[Dict[str, Any]] = []
        self.scratchpad: List[Dict[str, Any]] = []
        
        scratchpad_schema = {
            "type": "function",
            "function": {
                "name": "update_scratchpad",
                "description": "Update the task list on the scratchpad. Provide the *complete*, updated list of tasks.",
                "parameters": {"type": "object", "properties": {"tasks": {"type": "array", "description": "The complete, new list of tasks for the scratchpad.", "items": {"type": "object", "properties": {"task": {"type": "string"}, "completed": {"type": "boolean"}}, "required": ["task", "completed"]}}}, "required": ["tasks"]}
            }
        }
        
        user_tools = tools if tools else []
        self.tools = user_tools
        self.tool_schemas = [tool.schema for tool in self.tools] + [scratchpad_schema]
        self._available_tools = {tool.schema['function']['name']: tool for tool in self.tools}

    def update_scratchpad(self, tasks: List[Dict]) -> str:
        """An internal method to update the agent's scratchpad."""
        self.scratchpad = tasks
        formatted = ["Scratchpad updated:"] + [f"- [{'x' if item.get('completed') else ' '}] {item.get('task')}" for item in self.scratchpad]
        return "\n".join(formatted)

    def _inject_scratchpad_into_history(self, history: List[Dict]) -> List[Dict]:
        """Removes old scratchpad notes and re-injects the current state."""
        history_without_scratchpad = [msg for msg in history if not (msg.get("role") == "system" and msg.get("name") == "scratchpad_state")]
        if not self.scratchpad: return history_without_scratchpad

        formatted_content = ["CURRENT SCRATCHPAD STATE:"] + [f"- [{'x' if item.get('completed') else ' '}] {item.get('task')}" for item in self.scratchpad]
        scratchpad_message = {"role": "system", "name": "scratchpad_state", "content": "\n".join(formatted_content)}
        
        final_history = []
        if history_without_scratchpad and history_without_scratchpad[0].get("role") == "system":
            final_history.append(history_without_scratchpad[0])
            conversation = history_without_scratchpad[1:]
        else:
            conversation = history_without_scratchpad

        final_history.append(scratchpad_message)
        final_history.extend(conversation)
        return final_history

    def chat(self, max_tool_turns: int = 5, **kwargs) -> str:
        """Executes the full conversation loop and returns the final answer."""
        self.messages = self.prompt_processor.create_prompt(history=self.messages, **kwargs)
        
        for _ in range(max_tool_turns):
            history_with_scratchpad = self._inject_scratchpad_into_history(self._get_conversation_window())
            result = self.llm_processor.process(history_with_scratchpad, tools=self.tool_schemas, tool_choice="auto")
            
            if not result.thinking:
                self.messages.append(dict(result.message))
                return result.raw_content or "I could not generate a response."

            self.messages.append(dict(result.message))

            for tool_call in result.thinking:
                function_name = tool_call['function']['name']
                tool_output = ""
                try:
                    args = json.loads(tool_call['function']['arguments'])
                    if function_name == "update_scratchpad":
                        tool_output = self.update_scratchpad(**args)
                    else:
                        tool_to_run = self._available_tools.get(function_name)
                        if tool_to_run:
                            # The agent's responsibility is now much simpler: just execute.
                            tool_output = tool_to_run.execute(**args)
                        else:
                            raise ValueError(f"Tool '{function_name}' not found.")
                except Exception as e:
                    tool_output = f"An error occurred while executing tool '{function_name}': {e}"
                    print(tool_output)

                self.messages.append({"tool_call_id": tool_call['id'], "role": "tool", "name": function_name, "content": tool_output})
        
        return "Maximum number of turns reached. Could you please clarify your request?"

    def reset(self):
        """Clears the conversation history."""
        self.messages.clear()
        self.scratchpad.clear()

    def _get_conversation_window(self) -> List[Dict[str, Any]]:
        """Retrieves the conversation history, respecting the rolling window size."""
        if self.max_history_turns <= 0 or not self.messages:
            return self.messages

        system_messages = [msg for msg in self.messages if msg['role'] == 'system']
        conversation_messages = [msg for msg in self.messages if msg['role'] != 'system']
        
        user_message_indices = [i for i, msg in enumerate(conversation_messages) if msg.get('role') == 'user']
        start_index = user_message_indices[-self.max_history_turns] if len(user_message_indices) > self.max_history_turns else 0
            
        return system_messages + conversation_messages[start_index:]