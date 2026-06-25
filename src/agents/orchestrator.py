import logging
import time
from typing import List, Optional
from dataclasses import dataclass, field

from src.core.zai_chat import get_fallback_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from src.core.config import settings
from src.tools.tool_registry import ALL_TOOLS
from src.agents.memory import get_checkpointer, build_config
from src.agents.planner import Planner
from src.core.exceptions import AgentTimeoutError
from src.utils.llm_metadata import aggregate_usage

logger = logging.getLogger("agentic.orchestrator")

MAX_STEPS = 10


@dataclass
class AgentResult:
    """Structured result returned from the orchestrator."""
    final_answer: str
    steps: List[dict] = field(default_factory=list)
    tool_calls_made: List[str] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    model_name: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AgentOrchestrator:
    """
    ReAct Agent built with LangGraph's create_react_agent.
    - Uses ALL_TOOLS from the tool registry
    - Groq LLM (llama3-70b-8192) as the reasoning engine
    - Per-session memory via LangGraph MemorySaver checkpointer
    - Optional task planning via Planner
    """

    def __init__(self):
        self.llm = get_fallback_llm()
        self.checkpointer = get_checkpointer()
        self.planner = Planner()
        self.agent = create_react_agent(
            model=self.llm,
            tools=ALL_TOOLS,
            checkpointer=self.checkpointer,
        )

    def run(self, task: str, session_id: str) -> AgentResult:
        """
        Execute a task using the ReAct agent.
        1. Run Planner to decompose task into steps
        2. Execute agent with the full task (LangGraph handles ReAct internally)
        3. Collect steps, tool calls, and final answer
        """
        start = time.perf_counter()
        plan = self.planner.plan(task)
        config = build_config(session_id)
        steps_log = []
        tool_calls_made = []

        # Build an enriched prompt with the plan
        plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))
        enriched_input = (
            f"Task: {task}\n\n"
            f"Suggested plan (use as guidance, not strict instructions):\n{plan_text}"
        )

        ai_messages = []
        try:
            final_answer = ""
            step_count = 0

            for event in self.agent.stream(
                {"messages": [HumanMessage(content=enriched_input)]},
                config=config,
                stream_mode="values",
            ):
                step_count += 1
                if step_count > MAX_STEPS:
                    raise AgentTimeoutError(
                        f"Agent exceeded maximum step limit of {MAX_STEPS}."
                    )

                messages = event.get("messages", [])
                if not messages:
                    continue

                last_msg = messages[-1]
                msg_type = type(last_msg).__name__

                # Collect tool calls
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    for tc in last_msg.tool_calls:
                        tool_name = tc.get("name", "unknown")
                        tool_calls_made.append(tool_name)
                        steps_log.append({
                            "step": step_count,
                            "type": "tool_call",
                            "tool": tool_name,
                            "input": str(tc.get("args", {})),
                        })

                # Collect tool results
                if msg_type == "ToolMessage":
                    steps_log.append({
                        "step": step_count,
                        "type": "tool_result",
                        "tool": getattr(last_msg, "name", "unknown"),
                        "output": str(last_msg.content)[:500],
                    })

                # Extract final AI answer
                if msg_type == "AIMessage":
                    ai_messages.append(last_msg)
                    if last_msg.content:
                        final_answer = last_msg.content

            duration_ms = (time.perf_counter() - start) * 1000
            usage = aggregate_usage(ai_messages)
            model_name = usage["model_name"] or settings.CHAT_MODEL
            logger.info(
                "Agent completed task in %.1f ms | %d steps | tools: %s",
                duration_ms, step_count, tool_calls_made,
            )

            return AgentResult(
                final_answer=final_answer or "Task completed. No further output.",
                steps=steps_log,
                tool_calls_made=tool_calls_made,
                plan=plan,
                duration_ms=duration_ms,
                success=True,
                model_name=model_name,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
            )

        except AgentTimeoutError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            usage = aggregate_usage(ai_messages)
            logger.error("Agent timeout: %s", exc)
            return AgentResult(
                final_answer="",
                steps=steps_log,
                tool_calls_made=tool_calls_made,
                plan=plan,
                duration_ms=duration_ms,
                success=False,
                error=str(exc),
                model_name=usage.get("model_name") or settings.CHAT_MODEL,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            usage = aggregate_usage(ai_messages)
            logger.error("Agent error: %s", exc, exc_info=True)
            return AgentResult(
                final_answer="",
                steps=steps_log,
                tool_calls_made=tool_calls_made,
                plan=plan,
                duration_ms=duration_ms,
                success=False,
                error=str(exc),
                model_name=usage.get("model_name") or settings.CHAT_MODEL,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
