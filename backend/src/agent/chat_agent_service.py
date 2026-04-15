import json
import time
from typing import Generator

from backend.src.agent.memory.long_term_memory import LongTermMemoryService
from backend.src.agent.runtime.react_agent import ReactAgent
from backend.src.core.logger import logger


class ChatAgentService:
    def __init__(self):
        self.agent = ReactAgent()
        self.memory_service = LongTermMemoryService()
        self.stream_delay = 0.02

    def execute_stream(self, query: str, session_id: str, user_id: str) -> Generator[str, None, None]:
        memory_context = self.memory_service.build_memory_context(user_id, query)
        logger.info(
            "[ChatAgentService.execute_stream] session_id=%s user_id=%s memory_context=%s",
            session_id,
            user_id,
            memory_context.replace("\n", " | ") if memory_context else "",
        )
        return self.agent.execute_stream(query, session_id, memory_context)

    def reply(self, user_id: str, session_id: str, query: str) -> str:
        final_answer = ""
        for chunk in self.execute_stream(query=query, session_id=session_id, user_id=user_id):
            snapshot = chunk.strip()
            if not snapshot:
                continue
            final_answer = snapshot

        self.memory_service.extract_and_save(user_id, query, final_answer)
        return final_answer

    def reply_stream(self, user_id: str, session_id: str, query: str) -> Generator[str, None, None]:
        yield f"data: {json.dumps({'type': 'snapshot', 'content': '正在思考中...'}, ensure_ascii=False)}\n\n"
        final_answer = self.reply(user_id=user_id, session_id=session_id, query=query)

        for char in final_answer:
            yield f"data: {json.dumps({'type': 'delta', 'content': char}, ensure_ascii=False)}\n\n"
            time.sleep(self.stream_delay)

        yield f"data: {json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    service = ChatAgentService()
    demo_session_id = "chat-agent-service-demo-session"
    demo_user_id = "chat-agent-service-demo-user"
    demo_query = "我当前环境下怎么保养机器人？"

    print("正在思考中...")
    final_answer = service.reply(demo_user_id, demo_session_id, demo_query)

    for char in final_answer:
        print(char, end="", flush=True)
        time.sleep(0.02)
    print()
