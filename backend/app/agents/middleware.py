from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import ModelRequest, before_model, dynamic_prompt, wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from backend.app.agents.support.prompt_support import (
    append_memory_context,
    load_report_prompts,
    load_system_prompts,
)
from backend.app.core.logger import logger


@wrap_tool_call
def monitor_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    # 这个中间件会包住每一次工具调用，主要用于日志和少量上下文标记。
    logger.info("[tool monitor] running tool=%s args=%s", request.tool_call["name"], request.tool_call["args"])

    try:
        result = handler(request)
        logger.info("[tool monitor] tool succeeded: %s", request.tool_call["name"])

        # 一旦调用了报告场景的工具，就在运行时上下文里打上 `report=True` 标记。
        if request.tool_call["name"] == "fill_context_for_report":
            request.runtime.context["report"] = True

        return result
    except Exception as exc:
        logger.error("[tool monitor] tool failed: %s", str(exc))
        raise exc


@before_model
def log_before_model(state: AgentState, runtime: Runtime):
    # 在每次调用大模型之前记录一下消息数量和最新消息，便于排查上下文问题。
    logger.info("[log_before_model] calling model with %s messages", len(state["messages"]))
    logger.debug(
        "[log_before_model] latest=%s | %s",
        type(state["messages"][-1]).__name__,
        state["messages"][-1].content.strip(),
    )
    return None


# 在模型真正调用之前，动态生成这一次要用的 system prompt。
@dynamic_prompt
def build_dynamic_prompt(request: ModelRequest):
    # 根据运行时上下文切换不同的 system prompt。
    # 在此基础上追加 memory_context，让长期记忆以独立提示块的形式注入模型。
    memory_context = request.runtime.context.get("memory_context", "")
    if request.runtime.context.get("report", False):
        return append_memory_context(load_report_prompts(), memory_context)

    return append_memory_context(load_system_prompts(), memory_context)
