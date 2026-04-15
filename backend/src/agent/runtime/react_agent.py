from pathlib import Path
import sys
from typing import Generator

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[4]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from backend.src.agent.middleware.runtime_middleware import (
    build_dynamic_prompt,
    log_before_model,
    monitor_tool,
)
from backend.src.agent.support.prompt_support import load_system_prompts
from backend.src.agent.tools.agent_tools import (
    fetch_external_data,
    fill_context_for_report,
    get_current_month,
    get_user_id,
    get_user_location,
    get_weather,
    rag_summarize,
)
from backend.src.core.logger import logger
from backend.src.infra.llm.factory import chat_model


class ReactAgent:
    def __init__(self):
        self.checkpointer = InMemorySaver()
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
            middleware=[monitor_tool, log_before_model, build_dynamic_prompt],
            checkpointer=self.checkpointer,
        )

    def execute_stream(self, query: str, session_id: str, memory_context: str = "") -> Generator[str, None, None]:
        input_dict = {"messages": [{"role": "user", "content": query}]}
        config = {"configurable": {"thread_id": session_id}}

        for chunk in self.agent.stream(
            input=input_dict,
            config=config,
            stream_mode="values",
            context={"report": False, "memory_context": memory_context},
        ):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == "__main__":
    agent = ReactAgent()
    test_session_id = "react-agent-local-test"
    test_memory_context = "[长期记忆]\n- 所在城市：杭州\n- 已知偏好：静音、拖地"
    logger.info("[react_agent.__main__] memory_context=%s", test_memory_context)

    for chunk in agent.execute_stream("我当前环境下怎么保养机器人？", test_session_id, test_memory_context):
        print(chunk, end="", flush=True)
