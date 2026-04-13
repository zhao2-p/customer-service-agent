from typing import Generator

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from backend.app.agents.middleware import log_before_model, monitor_tool, report_prompt_switch
from backend.app.agents.support.prompt_support import load_system_prompts
from backend.app.agents.tools.agent_tools import (
    fetch_external_data,
    fill_context_for_report,
    get_current_month,
    get_user_id,
    get_user_location,
    get_weather,
    rag_summarize,
)
from backend.app.core.logger import logger
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

    def execute_stream(self, query: str, session_id: str, memory_context: str = "") -> Generator[str, None, None]:
        # 在 checkpointer 模式下，请求只提交本轮用户消息；历史由 thread_id 自动续接。
        # 长期记忆不直接混入历史消息，而是通过 runtime.context 注入到动态 prompt 中。
        input_dict = {"messages": [{"role": "user", "content": query}]}
        config = {"configurable": {"thread_id": session_id}}

        for chunk in self.agent.stream(
            input=input_dict,
            config=config,
            stream_mode="values",
            context={"report": False, "memory_context": memory_context},
        ):

            #打印完整的原生的消息
            # print("\n===== RAW CHUNK START =====")
            # print(chunk)
            # print("===== RAW CHUNK END =====\n")

            # print("===== RAW MESSAGES START =====")
            # print(chunk["messages"])
            # print("===== RAW MESSAGES END =====")

            # 打印完整消息
            # print("==== chunk messages ====")
            # for i, message in enumerate(chunk["messages"]):
            #     print(i, type(message).__name__, getattr(message, "content", None))

            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == "__main__":
    # 模块级测试代码：
    # 这里直接给一个模拟的 memory_context，便于验证长期记忆注入不会影响既有流式输出链路。
    agent = ReactAgent()
    test_session_id = "react-agent-local-test"
    test_memory_context = "[长期记忆]\n- 所在城市：杭州\n- 已知偏好：静音、拖地"
    logger.info("[react_agent.__main__] memory_context=%s", test_memory_context)

    for chunk in agent.execute_stream("我当前环境下怎么保养机器人", test_session_id, test_memory_context):
        print(chunk, end="", flush=True)

    # for chunk in agent.execute_stream("我叫什么名字", test_session_id, test_memory_context):
    #     print(chunk, end="", flush=True)
