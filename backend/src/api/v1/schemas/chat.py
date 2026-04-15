from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # 当前用户问题。
    query: str = Field(..., examples=["小户型适合哪些扫地机器人？"])
    # session_id 用于把同一会话请求路由到同一个 LangGraph thread。
    session_id: str = Field(..., examples=["demo-session-id"])
    # user_id 用于标识“同一个用户”，长期记忆必须绑定它，而不能绑定 session_id。
    # 这样用户即使重开会话，只要 user_id 不变，仍然可以读取到之前沉淀下来的长期记忆。
    user_id: str = Field(..., examples=["demo-user-id"])
