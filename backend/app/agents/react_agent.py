from langchain.agents import create_agent
from typing import Generator

from backend.app.agents.middleware import log_before_model, monitor_tool, report_prompt_switch
from backend.app.agents.services.prompt_service import load_system_prompts
from backend.app.agents.tools.agent_tools import (
    fetch_external_data,
    fill_context_for_report,
    get_current_month,
    get_user_id,
    get_user_location,
    get_weather,
    rag_summarize,
)
from backend.app.infra.llm.factory import chat_model


class ReactAgent:
    def __init__(self):
        # 先保留最近 N 条有效对话，避免上下文无限膨胀。
        self.max_history_messages = 10
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[
                rag_summarize,
                get_weather,
                get_user_location,
                get_user_id,
                get_current_month,
                fetch_external_data,
                fill_context_for_report,
            ],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )

    def execute_stream(self, query: str, history: list[dict] | None = None) -> Generator[str, None, None]:
        # 仅保留结构完整的 user/assistant 消息，避免脏数据进入 Agent 上下文。
        valid_history = [
            {"role": message["role"], "content": message["content"]}
            for message in (history or [])
            if message.get("role") in {"user", "assistant"} and message.get("content")
        ]
        short_term_memory = valid_history[-self.max_history_messages :]
        input_dict = {"messages": short_term_memory + [{"role": "user", "content": query}]}

        # 这里保留流式接口，后续无论是 CLI、WebSocket 还是 SSE 都能复用。
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == "__main__":
    agent = ReactAgent()
    for chunk in agent.execute_stream("我现在的环境下应该怎么保养机器人？"):
        print(chunk, end="", flush=True)
