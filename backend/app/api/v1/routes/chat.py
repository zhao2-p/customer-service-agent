from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.api.v1.schemas.chat import ChatRequest
from backend.app.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()


@router.post("/stream")
def chat_stream(request: ChatRequest):
    # session_id 会被下游作为 thread_id 使用，由 checkpointer 托管短期记忆。
    # 同时新增 user_id，供下游读取和写入跨会话长期记忆。
    return StreamingResponse(
        chat_service.event_stream(request.query, request.session_id, request.user_id),
        media_type="text/event-stream",
        # 这些头可以尽量减少中间层缓存或缓冲，帮助前端及时拿到每个 SSE 事件。
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
