from typing import Any, Optional

from langchain_core.messages import BaseMessage


def extract_llm_usage(message: BaseMessage) -> dict:
    """Extract model name and token counts from a LangChain AIMessage."""
    meta = getattr(message, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}

    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    total_tokens = usage.get("total_tokens") or (prompt_tokens + completion_tokens)

    model_name = (
        meta.get("model_name")
        or meta.get("model")
        or getattr(message, "name", None)
        or ""
    )

    return {
        "model_name": model_name,
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


def aggregate_usage(messages: list) -> dict:
    """Sum token usage across multiple AIMessages."""
    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    model_name = ""

    for msg in messages:
        if type(msg).__name__ != "AIMessage":
            continue
        usage = extract_llm_usage(msg)
        total_prompt += usage["prompt_tokens"]
        total_completion += usage["completion_tokens"]
        total_tokens += usage["total_tokens"]
        if usage["model_name"]:
            model_name = usage["model_name"]

    return {
        "model_name": model_name,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_tokens,
    }
