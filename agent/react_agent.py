from langchain.agents import create_agent

from agent.tools.agent_tools import (
    fetch_external_data,
    fill_context_for_report,
    get_current_month,
    get_user_id,
    get_user_location,
    get_weather,
    rag_summarize,
)
from agent.tools.middleware import log_before_model, monitor_tool, report_prompt_switch
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts


class ReactAgent:
    def __init__(self):
        # 短期记忆窗口大小。
        # 每次调用模型时，不把整段历史全部传进去，而是只保留最近 10 条消息。
        # 这样既能保留“刚刚聊过什么”的上下文，又能避免上下文无限膨胀。
        self.max_history_messages = 10

        # 创建 Agent。
        # 这里封装了：
        # 1. 模型本身 chat_model
        # 2. 系统提示词 system_prompt
        # 3. 可调用的工具 tools
        # 4. 执行前后的中间件 middleware
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

    def execute_stream(self, query: str, history: list[dict] | None = None):
        """
        流式执行智能体，并把模型输出逐段返回给上层页面。

        参数：
        - query:
            当前这一轮用户输入的问题。
        - history:
            当前会话之前的历史消息列表。
            约定格式如下：
            [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]

        这个方法是“短期记忆”的核心入口。
        原来的代码只把当前 query 传给模型，所以模型每一轮都像是重新开始。
        现在会把最近若干条 history 一起传入，让模型能基于前文继续回答。
        """

        # 清洗历史消息：
        # 只保留结构完整的 user / assistant 消息。
        valid_history = [
            {"role": message["role"], "content": message["content"]}
            for message in (history or [])
            if message.get("role") in {"user", "assistant"} and message.get("content")
        ]

        # 截断历史，只保留最近 N 条消息，形成短期记忆窗口。
        # 例如 max_history_messages = 10 时：
        # 如果历史有 20 条，只会取最后 10 条；
        # 如果历史不足 10 条，就全部保留。
        short_term_memory = valid_history[-self.max_history_messages:]

        # 组装发给 Agent 的消息列表。
        # 顺序必须是：
        # 1. 先放历史 short_term_memory
        # 2. 再放当前轮用户输入 query
        # 这样模型看到的是完整连续对话，而不是单轮孤立问题。
        input_dict = {
            "messages": short_term_memory + [{"role": "user", "content": query}],
        }

        # 以流式方式执行 Agent。
        # stream_mode="values" 会持续返回执行过程中的最新状态。
        # context={"report": False} 是运行时上下文，
        # 中间件 report_prompt_switch 会根据这个值决定是否切换成“报告生成”的提示词。
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            # chunk 中包含当前阶段的消息列表。
            # 最后一条消息就是这个阶段最新生成/更新的消息。
            latest_message = chunk["messages"][-1]

            # 如果有文本内容，就把它返回给前端，供 Streamlit 做流式展示。
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == "__main__":
    agent = ReactAgent()

    # 本地调试入口。
    # 这里直接测试单轮问题是否能正常跑通。
    for chunk in agent.execute_stream("我叫什么名字？"):
        print(chunk, end="", flush=True)
