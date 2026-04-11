from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import ModelRequest, before_model, dynamic_prompt, wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from backend.app.core.logger import logger
from backend.app.services.prompt_service import load_report_prompts, load_system_prompts


@wrap_tool_call
def monitor_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    logger.info("[tool monitor] running tool=%s args=%s", request.tool_call["name"], request.tool_call["args"])

    try:
        result = handler(request)
        logger.info("[tool monitor] tool succeeded: %s", request.tool_call["name"])

        if request.tool_call["name"] == "fill_context_for_report":
            request.runtime.context["report"] = True

        return result
    except Exception as exc:
        logger.error("[tool monitor] tool failed: %s", str(exc))
        raise exc


@before_model
def log_before_model(state: AgentState, runtime: Runtime):
    logger.info("[log_before_model] calling model with %s messages", len(state["messages"]))
    logger.debug(
        "[log_before_model] latest=%s | %s",
        type(state["messages"][-1]).__name__,
        state["messages"][-1].content.strip(),
    )
    return None


@dynamic_prompt
def report_prompt_switch(request: ModelRequest):
    if request.runtime.context.get("report", False):
        return load_report_prompts()

    return load_system_prompts()
