from typing import Generator

from langchain.agents import create_agent
from langchain_classic.chains.question_answering.map_reduce_prompt import messages
from langgraph.checkpoint.memory import InMemorySaver

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
        # 同一个 ReactAgent 实例内，不同 thread_id 的短期记忆由 checkpointer 托管。
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
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
            checkpointer=self.checkpointer,
        )

    def execute_stream(self, query: str, session_id: str) -> Generator[str, None, None]:
        # 在 checkpointer 模式下，请求只提交本轮用户消息；历史由 thread_id 自动续接。
        input_dict = {"messages": [{"role": "user", "content": query}]}
        config = {"configurable": {"thread_id": session_id}}

        for chunk in self.agent.stream(
            input_dict,
            config=config,
            stream_mode="values",
            context={"report": False},
        ):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == "__main__":
    agent = ReactAgent()
    test_session_id = "react-agent-local-test"
    for chunk in agent.execute_stream("小户型适合哪些扫地机器人", test_session_id):
        print(chunk, end="", flush=True)

    # for chunk in agent.execute_stream("我叫什么名字", test_session_id):
    #     print(chunk, end="", flush=True)
