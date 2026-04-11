import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.agents.react_agent import ReactAgent


router = APIRouter(prefix="/chat", tags=["chat"])
# 先复用单例 Agent，后续如果引入会话隔离或依赖注入，再改成工厂/Provider。
agent = ReactAgent()


class ChatMessage(BaseModel):
    role: str = Field(..., examples=["user"])
    content: str = Field(..., examples=["你好"])


class ChatRequest(BaseModel):
    query: str = Field(..., examples=["小户型适合哪些扫地机器人？"])
    history: list[ChatMessage] = Field(default_factory=list)


@router.post("/stream")
def chat_stream(request: ChatRequest):
    history = [message.model_dump() for message in request.history]

    def event_stream():
        final_answer = ""
        yield f"data: {json.dumps({'type': 'snapshot', 'content': '正在思考...'}, ensure_ascii=False)}\n\n"

        for chunk in agent.execute_stream(request.query, history):
            snapshot = chunk.strip()
            if not snapshot:
                continue

            final_answer = snapshot

        yield f"data: {json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
