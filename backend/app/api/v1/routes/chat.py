from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.api.v1.schemas.chat import ChatRequest
from backend.app.services.chat_service import ChatService


# APIRouter 可以理解为 FastAPI 里“某一组接口”的路由容器。
router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()


@router.post("/stream")
def chat_stream(request: ChatRequest):
    # Pydantic 模型先转成普通 dict，再交给业务层和 Agent 使用。
    history = [message.model_dump() for message in request.history]
    # StreamingResponse 会把生成过程按流式响应发给前端，适合聊天场景。
    return StreamingResponse(chat_service.event_stream(request.query, history), media_type="text/event-stream")
