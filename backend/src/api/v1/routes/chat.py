from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.src.agent.chat_agent_service import ChatAgentService
from backend.src.api.v1.schemas.chat import ChatRequest


router = APIRouter(prefix="/chat", tags=["chat"])
chat_agent_service = ChatAgentService()


@router.post("/stream")
def chat_stream(request: ChatRequest):
    # session_id 会被下游作为 thread_id 使用，由 checkpointer 托管短期记忆。
    # 同时新增 user_id，供下游读取和写入跨会话长期记忆。
    return StreamingResponse(
        chat_agent_service.reply_stream(
            user_id=request.user_id,
            session_id=request.session_id,
            query=request.query,
        ),
        media_type="text/event-stream",
        # 这些头可以尽量减少中间层缓存或缓冲，帮助前端及时拿到每个 SSE 事件。
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
