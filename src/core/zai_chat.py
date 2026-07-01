import json
import logging
from typing import List, Optional, Any, Dict, Sequence, Union, Type, Callable
import httpx
from pydantic import ConfigDict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_core.runnables import Runnable

logger = logging.getLogger("agentic.zai")


class ChatZAI(BaseChatModel):
    """
    Custom LangChain chat model wrapper for Z.ai GLM API.
    Converts messages to/from OpenAI schema, handles tool calls, and communicates via HTTP POST.
    """
    api_key: str
    base_url: str = "https://api.z.ai/api/paas/v4/chat/completions"
    model_name: str = "glm-5.2"
    temperature: float = 1.0

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any
    ) -> ChatResult:
        payload_messages = []
        for msg in messages:
            payload_messages.append(self._convert_message_to_dict(msg))

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": payload_messages,
            "stream": False,
            "temperature": self.temperature,
        }

        # Handle tool calling if tools are bound
        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]

        headers = {
            "Accept-Language": "en-US,en",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                response_json = response.json()
        except Exception as exc:
            logger.error("ChatZAI API request failed: %s", exc)
            raise

        choice = response_json["choices"][0]
        message_dict = choice["message"]
        content = message_dict.get("content") or ""
        tool_calls = []

        if "tool_calls" in message_dict and message_dict["tool_calls"]:
            for tc in message_dict["tool_calls"]:
                func = tc["function"]
                args_str = func.get("arguments") or "{}"
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = args_str
                tool_calls.append({
                    "name": func["name"],
                    "args": args,
                    "id": tc.get("id"),
                })

        ai_message = AIMessage(
            content=content,
            tool_calls=tool_calls,
            response_metadata={
                "model_name": self.model_name,
                "token_usage": {
                    "prompt_tokens": (response_json.get("usage") or {}).get("prompt_tokens", 0),
                    "completion_tokens": (response_json.get("usage") or {}).get("completion_tokens", 0),
                    "total_tokens": (response_json.get("usage") or {}).get("total_tokens", 0),
                },
            },
        )

        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def _convert_message_to_dict(self, message: BaseMessage) -> dict:
        if isinstance(message, SystemMessage):
            return {"role": "system", "content": message.content}
        elif isinstance(message, HumanMessage):
            return {"role": "user", "content": message.content}
        elif isinstance(message, AIMessage):
            res = {"role": "assistant", "content": message.content or ""}
            if message.tool_calls:
                res["tool_calls"] = [
                    {
                        "id": tc.get("id"),
                        "type": "function",
                        "function": {
                            "name": tc.get("name"),
                            "arguments": json.dumps(tc.get("args")) if isinstance(tc.get("args"), dict) else tc.get("args")
                        }
                    }
                    for tc in message.tool_calls
                ]
            return res
        elif isinstance(message, ToolMessage):
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content
            }
        else:
            return {"role": "user", "content": message.content}

    def bind_tools(self, tools: list, **kwargs: Any) -> Any:
        formatted_tools = [convert_to_openai_tool(t) for t in tools]
        return self.bind(tools=formatted_tools, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "zai"


class FallbackChatModel(BaseChatModel):
    """
    Fallback Chat Model wrapper.
    Receives primary and secondary LLM runnables. Tries primary first; on failure,
    logs the warning and executes the secondary.
    """
    primary: Runnable
    secondary: Runnable

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any
    ) -> ChatResult:
        # Standard _generate path for direct execution (e.g. invoke delegates here)
        try:
            if hasattr(self.primary, "_generate"):
                return self.primary._generate(messages, stop=stop, **kwargs)
            else:
                res = self.primary.invoke(messages, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=res)])
        except Exception as exc:
            logger.warning("Primary model failed in _generate: %s. Falling back to secondary.", exc)
            if hasattr(self.secondary, "_generate"):
                return self.secondary._generate(messages, stop=stop, **kwargs)
            else:
                res = self.secondary.invoke(messages, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=res)])

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        try:
            return self.primary.invoke(input, config=config, **kwargs)
        except Exception as exc:
            logger.warning("Primary model invoke failed: %s. Falling back to secondary.", exc)
            return self.secondary.invoke(input, config=config, **kwargs)

    def stream(self, input: Any, config: Optional[Any] = None, **kwargs: Any):
        try:
            yield from self.primary.stream(input, config=config, **kwargs)
        except Exception as exc:
            logger.warning("Primary model stream failed: %s. Falling back to secondary.", exc)
            yield from self.secondary.stream(input, config=config, **kwargs)

    def bind_tools(self, tools: list, **kwargs: Any) -> Any:
        # Wrap primary and secondary bound runnables in a new FallbackChatModel instance
        bound_primary = self.primary.bind_tools(tools, **kwargs)
        bound_secondary = self.secondary.bind_tools(tools, **kwargs)
        return FallbackChatModel(primary=bound_primary, secondary=bound_secondary)

    @property
    def _llm_type(self) -> str:
        return "fallback"


def get_fallback_llm() -> FallbackChatModel:
    """
    Helper to initialize the default FallbackChatModel using the application's configuration settings.
    Primary: ChatZAI (GLM-5.2) when a real API key is configured
    Secondary: ChatGroq (llama-3.3-70b-versatile)
    """
    from langchain_groq import ChatGroq
    from src.core.config import settings

    secondary = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.CHAT_MODEL,
    )

    zai_key = (settings.ZAI_API_KEY or "").strip()
    if not zai_key or zai_key == "your-zai-token":
        logger.info("Z.ai API key not configured — using Groq directly.")
        return FallbackChatModel(primary=secondary, secondary=secondary)

    primary = ChatZAI(
        api_key=zai_key,
        base_url=settings.ZAI_BASE_URL,
        model_name=settings.ZAI_MODEL,
    )

    return FallbackChatModel(primary=primary, secondary=secondary)
