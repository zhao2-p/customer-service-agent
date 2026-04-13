import json
from typing import Generator

from backend.app.agents.react_agent import ReactAgent
from backend.app.core.logger import logger
from backend.app.services.memory_service import MemoryService


class ChatService:
    def __init__(self):
        self.agent = ReactAgent()
        self.memory_service = MemoryService()    # 获取长期记忆服务

    # 获取agent的返回值并执行的流式输出
    def execute_stream(self, query: str, session_id: str, user_id: str) -> Generator[str, None, None]:
        # 短期记忆交给 agent 内部的 checkpointer 管理。
        # 长期记忆在进入 agent 之前先读取并拼成独立的 memory_context。
        memory_context = self.memory_service.build_memory_context(user_id, query)
        logger.info(
            "[ChatService.execute_stream] session_id=%s user_id=%s memory_context=%s",
            session_id,
            user_id,
            memory_context.replace("\n", " | ") if memory_context else "",
        )
        return self.agent.execute_stream(query, session_id, memory_context)

    # 构建最终的流式输出
    def event_stream(self, query: str, session_id: str, user_id: str) -> Generator[str, None, None]:
        final_answer = ""
        yield f"data: {json.dumps({'type': 'snapshot', 'content': '正在思考中...'}, ensure_ascii=False)}\n\n"

        for chunk in self.execute_stream(query, session_id, user_id):
            snapshot = chunk.strip()
            if not snapshot:
                continue

            # 当前前端仍然只展示最终答案，因此只保留最后一次快照。
            final_answer = snapshot

        # 回答完成之后再写入长期记忆，避免中途流式片段反复触发写入。
        self.memory_service.extract_and_save(user_id, query, final_answer)
        yield f"data: {json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    # 模块级测试代码：
    # 直接运行 `python -m backend.app.services.chat_service`，
    # 可验证长期记忆读取、Agent 调用和最终写入流程能否串起来。
    service = ChatService()
    demo_session_id = "chat-service-demo-session"
    demo_user_id = "chat-service-demo-user"
    #demo_query = "我住在杭州，家里有猫，预算3000元以内，以后推荐时记住我更看重静音和拖地。"
    demo_query = "我当前环境下怎么保养机器人"

    for event in service.event_stream(demo_query, demo_session_id, demo_user_id):
        print(event, end="")
