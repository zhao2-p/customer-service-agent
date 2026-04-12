from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # 当前用户问题。
    query: str = Field(..., examples=["小户型适合哪些扫地机器人？"])
    # session_id 用于把同一会话请求路由到同一个 LangGraph thread。
    session_id: str = Field(..., examples=["demo-session-id"])
