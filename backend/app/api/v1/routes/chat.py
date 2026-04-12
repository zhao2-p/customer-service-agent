from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["chat"])
# 路由层只负责接收请求并把处理委托给应用服务。
chat_service = ChatService()


class ChatMessage(BaseModel):
    role: str = Field(..., examples=["user"])
    content: str = Field(..., examples=["你好"])


class ChatRequest(BaseModel):
    query: str = Field(..., examples=["小户型适合哪些扫地机器人？"])
    history: list[ChatMessage] = Field(default_factory=list)


@router.post("/stream")
def chat_stream(request: ChatRequest):
    # 将 Pydantic 模型转换成 agent 可消费的对话历史结构。
    history = [message.model_dump() for message in request.history]
    return StreamingResponse(chat_service.event_stream(request.query, history), media_type="text/event-stream")
