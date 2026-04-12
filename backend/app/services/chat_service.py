import json
from typing import Generator

from backend.app.agents.react_agent import ReactAgent


class ChatService:
    def __init__(self):
        # Service 层负责衔接 API 层和 Agent 层。
        self.agent = ReactAgent()

    def execute_stream(self, query: str, history: list[dict] | None = None) -> Generator[str, None, None]:
        # 保留 Agent 原始文本流，便于后续复用到 SSE 之外的输出方式。
        return self.agent.execute_stream(query, history)

    def event_stream(self, query: str, history: list[dict] | None = None) -> Generator[str, None, None]:
        # 这里把 Agent 文本流包装成 SSE 事件流，前端可以边收边展示。
        final_answer = ""
        yield f"data: {json.dumps({'type': 'snapshot', 'content': '正在思考...'}, ensure_ascii=False)}\n\n"

        for chunk in self.execute_stream(query, history):
            snapshot = chunk.strip()
            if not snapshot:
                continue

            # 当前前端只展示最终答案，所以这里持续覆盖最后一次结果。
            final_answer = snapshot

        yield f"data: {json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)}\n\n"
