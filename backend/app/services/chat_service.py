import json
import time
from typing import Generator

from backend.app.agents.react_agent import ReactAgent
from backend.app.core.logger import logger
from backend.app.services.memory_service import MemoryService


class ChatService:
    def __init__(self):
        self.agent = ReactAgent()
        self.memory_service = MemoryService()  # 获取长期记忆服务
        self.stream_delay = 0.02  # 给前端一个可感知的字级输出节奏，避免所有字符几乎同时出现

    # 获取 agent 的返回结果并执行流式输出
    def execute_stream(self, query: str, session_id: str, user_id: str) -> Generator[str, None, None]:
        # 短期记忆交给 agent 内部的 checkpointer 管理
        # 长期记忆在进入 agent 之前先读取并拼成独立的 memory_context
        memory_context = self.memory_service.build_memory_context(user_id, query)
        logger.info(
            "[ChatService.execute_stream] session_id=%s user_id=%s memory_context=%s",
            session_id,
            user_id,
            memory_context.replace("\n", " | ") if memory_context else "",
        )
        return self.agent.execute_stream(query, session_id, memory_context)

    # 构建提供给前端页面使用的 SSE 流。
    # 这里继续只保留最终答案，但把最终答案拆成字级 delta 事件交给前端逐字渲染。
    def event_stream(self, query: str, session_id: str, user_id: str) -> Generator[str, None, None]:
        final_answer = ""
        yield f"data: {json.dumps({'type': 'snapshot', 'content': '正在思考中...'}, ensure_ascii=False)}\n\n"

        for chunk in self.execute_stream(query, session_id, user_id):
            snapshot = chunk.strip()
            if not snapshot:
                continue

            # 前端只展示最终回复，因此这里只保留最后一次快照。
            final_answer = snapshot

        # 回答完成之后再写入长期记忆，避免中途增量事件重复触发写入。
        self.memory_service.extract_and_save(user_id, query, final_answer)

        for char in final_answer:
            yield f"data: {json.dumps({'type': 'delta', 'content': char}, ensure_ascii=False)}\n\n"
            # 给浏览器一个可感知的节奏，避免所有字符几乎同时到达。
            time.sleep(self.stream_delay)

        yield f"data: {json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    # 模块级测试代码：
    # 直接运行 `python -m backend.app.services.chat_service`
    # 可验证长期记忆读取、Agent 调用和最终写入流程能否串起来。
    service = ChatService()
    demo_session_id = "chat-service-demo-session"
    demo_user_id = "chat-service-demo-user"
    # demo_query = "我住在杭州，家里有猫，预算3000元以内，以后推荐时记住我更看重静音和拖地。"
    demo_query = "我当前环境下怎么保养机器人？"

    print("正在思考中...")

    final_answer = ""
    for chunk in service.execute_stream(demo_query, demo_session_id, demo_user_id):
        snapshot = chunk.strip()
        if not snapshot:
            continue

        # 模块测试里保留中间过程，但不做中间过程的逐字流式，方便直接观察 Message 内容变化。
        print(snapshot)
        final_answer = snapshot

    # 回答完成之后再写入长期记忆，保持和正式链路一致。
    service.memory_service.extract_and_save(demo_user_id, demo_query, final_answer)

    for char in final_answer:
        print(char, end="", flush=True)
        time.sleep(0.02)
    print()
