import json
from typing import Generator
import time

from backend.app.agents.react_agent import ReactAgent


class ChatService:
    def __init__(self):
        self.agent = ReactAgent()

    def execute_stream(self, query: str, session_id: str) -> Generator[str, None, None]:
        # 短期记忆交给 agent 内部的 checkpointer 管理。
        return self.agent.execute_stream(query, session_id)

    def event_stream(self, query: str, session_id: str) -> Generator[str, None, None]:
        final_answer = ""
        yield f"data: {json.dumps({'type': 'snapshot', 'content': '正在思考中...'}, ensure_ascii=False)}\n\n"

        for chunk in self.execute_stream(query, session_id):
            snapshot = chunk.strip()
            if not snapshot:
                continue

            # 当前前端仍然只展示最终答案，因此只保留最后一次快照。
            final_answer = snapshot

        yield f"data: {json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)}\n\n"