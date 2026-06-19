from typing import TypedDict, Annotated, List, Any, Optional
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """
    The state that flows through the LangGraph ReAct agent graph.
    - messages:       Conversation history (accumulated with operator.add)
    - plan:           List of planned sub-task strings from the Planner
    - current_step:   Index of the current plan step being executed
    - observations:   List of raw tool output strings collected so far
    - tool_results:   Structured list of {tool, input, output} dicts
    - final_answer:   The agent's final response string
    - error:          Error message if something went wrong
    """
    messages: Annotated[List[BaseMessage], operator.add]
    plan: List[str]
    current_step: int
    observations: List[str]
    tool_results: List[dict]
    final_answer: Optional[str]
    error: Optional[str]
