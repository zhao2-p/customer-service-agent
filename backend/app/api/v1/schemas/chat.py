from pydantic import BaseModel, Field


# Pydantic 模型负责定义接口的请求/响应数据结构。
# FastAPI 会基于这些模型自动完成参数校验和文档生成。
class ChatMessage(BaseModel):
    role: str = Field(..., examples=["user"])
    content: str = Field(..., examples=["你好"])


class ChatRequest(BaseModel):
    # 当前用户问题。
    query: str = Field(..., examples=["小户型适合哪些扫地机器人？"])
    # 前端传来的历史消息，用于给 Agent 保留上下文。
    history: list[ChatMessage] = Field(default_factory=list)
