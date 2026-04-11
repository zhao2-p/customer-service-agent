from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.routes.chat import router as chat_router
from backend.app.api.v1.routes.health import router as health_router


app = FastAPI(
    title="AI Agent System",
    version="0.1.0",
    description="Backend API for the AI RAG and agent system.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 前后端分离后，前端页面通过 `/api/v1/*` 调用后端接口。
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
