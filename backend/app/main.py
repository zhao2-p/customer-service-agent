from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.routes.chat import router as chat_router
from backend.app.api.v1.routes.health import router as health_router


# FastAPI 应用对象相当于后端服务的“总入口”。
# 启动 `uvicorn backend.app.main:app --reload` 时，Uvicorn 会加载这里的 `app`。
app = FastAPI(
    title="AI Agent System",
    version="0.1.0",
    description="Backend API for the AI RAG and agent system.",
)

# CORS 允许浏览器里的前端页面跨域调用这个后端接口。
# 这里全部放开，方便本地联调。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 把不同模块的路由统一挂到 `/api/v1` 前缀下。
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
