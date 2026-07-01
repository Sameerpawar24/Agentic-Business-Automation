import uuid
import logging
import time
from typing import Generator, Optional, Annotated

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage
from src.core.zai_chat import get_fallback_llm
from src.core.config import settings
from src.agents.memory import get_checkpointer, build_config
from src.services.log_service import LogService
from src.utils.llm_metadata import extract_llm_usage

logger = logging.getLogger("agentic.chat_service")


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


def _is_assistant_chunk(msg) -> bool:
    return type(msg).__name__ in ("AIMessage", "AIMessageChunk")


class ChatService:
    """
    Service for general chat conversation.
    Uses the fallback LLM model and LangGraph's MemorySaver to persist history per session_id.
    """

    def __init__(self, api_key: str = None):
        self.llm = get_fallback_llm()
        self.checkpointer = get_checkpointer()
        self.log_service = LogService()

        workflow = StateGraph(ChatState)

        def call_model(state: ChatState):
            return {"messages": [self.llm.invoke(state["messages"])]}

        workflow.add_node("model", call_model)
        workflow.add_edge(START, "model")
        workflow.add_edge("model", END)
        self.chat_graph = workflow.compile(checkpointer=self.checkpointer)

    def _resolve_session_id(self, session_id: Optional[str]) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info("Generated new session ID: %s", session_id)
        return session_id

    def _log_chat(
        self,
        *,
        session_id: str,
        message: str,
        response_text: str,
        final_msg,
        start: float,
        success: bool,
        error: Optional[str],
    ) -> None:
        latency_ms = (time.perf_counter() - start) * 1000
        usage = extract_llm_usage(final_msg) if final_msg else {}
        model_name = usage.get("model_name") or settings.CHAT_MODEL
        try:
            self.log_service.create(
                log_type="chat",
                session_id=session_id,
                message=message,
                response=response_text if success else None,
                model_name=model_name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=round(latency_ms, 2),
                success=success,
                error=error,
            )
        except Exception as log_exc:
            logger.warning("Could not persist chat activity log: %s", log_exc)

    def run_chat(self, message: str, session_id: Optional[str] = None) -> dict:
        """Send a message and return the full response (non-streaming)."""
        session_id = self._resolve_session_id(session_id)
        config = build_config(session_id)
        start = time.perf_counter()
        success = True
        error = None
        final_msg = None
        response_text = ""

        try:
            result = self.chat_graph.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config,
            )
            final_msg = result["messages"][-1]
            response_text = final_msg.content
        except Exception as exc:
            success = False
            error = str(exc)
            logger.error("Chat failed for session %s: %s", session_id, exc, exc_info=True)
            raise
        finally:
            self._log_chat(
                session_id=session_id,
                message=message,
                response_text=response_text,
                final_msg=final_msg,
                start=start,
                success=success,
                error=error,
            )

        return {"response": response_text, "session_id": session_id}

    def stream_chat(
        self, message: str, session_id: Optional[str] = None
    ) -> Generator[str, None, dict]:
        """
        Stream assistant tokens via SSE-friendly string yields.
        Returns metadata dict when the generator is exhausted (use .send or capture final return).
        """
        session_id = self._resolve_session_id(session_id)
        config = build_config(session_id)
        start = time.perf_counter()
        success = True
        error = None
        final_msg = None
        response_text = ""

        try:
            for msg, _metadata in self.chat_graph.stream(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                stream_mode="messages",
            ):
                if _is_assistant_chunk(msg) and msg.content:
                    response_text += msg.content
                    yield msg.content

            snapshot = self.chat_graph.get_state(config)
            if snapshot and snapshot.values.get("messages"):
                final_msg = snapshot.values["messages"][-1]
                if hasattr(final_msg, "content") and final_msg.content:
                    response_text = final_msg.content

        except Exception as exc:
            success = False
            error = str(exc)
            logger.error("Chat stream failed for session %s: %s", session_id, exc, exc_info=True)
            raise
        finally:
            self._log_chat(
                session_id=session_id,
                message=message,
                response_text=response_text,
                final_msg=final_msg,
                start=start,
                success=success,
                error=error,
            )

        return {"response": response_text, "session_id": session_id}

    def send_message(self, message: str) -> str:
        res = self.run_chat(message, session_id=str(uuid.uuid4()))
        return res["response"]

    def invoke(self, message: str) -> str:
        return self.send_message(message)
