import json
from typing import Generator

from backend.app.agents.react_agent import ReactAgent


class ChatService:
    def __init__(self):
        self.agent = ReactAgent()

    def execute_stream(self, query: str, history: list[dict] | None = None) -> Generator[str, None, None]:
        # 保留 agent 原始文本流，便于后续复用到 SSE 之外的输出方式。
        return self.agent.execute_stream(query, history)

    def event_stream(self, query: str, history: list[dict] | None = None) -> Generator[str, None, None]:
        # 将 agent 文本流包装成前端可直接消费的 SSE 事件流。
        final_answer = ""
        yield f"data: {json.dumps({'type': 'snapshot', 'content': '正在思考...'}, ensure_ascii=False)}\n\n"

        for chunk in self.execute_stream(query, history):
            snapshot = chunk.strip()
            if not snapshot:
                continue

            final_answer = snapshot

        yield f"data: {json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)}\n\n"
