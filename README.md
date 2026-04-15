# 智能客服系统

一个面向扫地机器人与扫拖一体机场景的智能客服项目，当前采用前后端分离架构，核心链路基于 `Agent + RAG + LLM + 长期记忆`。

目前项目已经具备这些能力：

- 基于知识库的问答
- Agent 工具调用与多步处理
- Chroma 向量库检索
- 基于 `session_id` 的短期会话记忆
- 基于 `user_id` 的长期记忆注入与持久化
- 通过 SSE 将最终答案流式返回到前端

## 项目结构

```text
customer_service_agent/
├─ backend/
│  ├─ app/
│  │  ├─ api/                 # FastAPI 路由与请求模型
│  │  ├─ agents/              # Agent、工具、中间件、提示词
│  │  ├─ core/                # 配置、路径、日志
│  │  ├─ infra/               # LLM、向量库、文件、记忆存储
│  │  ├─ services/            # 聊天服务、长期记忆服务
│  │  └─ main.py              # FastAPI 入口
│  ├─ data/                   # 知识库原始数据、外部数据、长期记忆数据库
│  ├─ chroma_db/              # Chroma 持久化目录
│  └─ logs/                   # 运行日志
├─ config/                    # YAML 配置
├─ frontend/                  # 原生 HTML/CSS/JS 前端页面
├─ requirements.txt
├─ 技术文档.md
└─ 长期记忆设计稿.md
```

## 当前架构

后端使用 `FastAPI` 提供接口，前端使用原生 `HTML + CSS + JavaScript`。

聊天主链路如下：

1. 前端提交 `query`、`session_id`、`user_id`
2. 后端先根据 `user_id` 读取长期记忆，构造 `memory_context`
3. Agent 按需调用 RAG、天气、外部数据等工具
4. Agent 生成最终答案
5. 后端把最终答案按字符拆分，通过 SSE 流式返回前端
6. 回答结束后，再从本轮输入中抽取可沉淀的长期记忆并写入 SQLite

## 配置说明

项目当前主要依赖这些配置文件：

- `config/rag.yml`：聊天模型、Embedding 模型
- `config/chroma.yml`：Chroma 持久化目录、知识库目录、切分参数
- `config/agent.yml`：外部数据源路径
- `config/prompts.yml`：提示词文件路径
- `config/memory.yml`：长期记忆 SQLite 路径、注入条数、规则抽取开关

当前默认配置中：

- 聊天模型：`qwen-plus`
- 向量模型：`text-embedding-v4`
- 知识库目录：`backend/data/knowledge`
- 长期记忆库：`backend/database/memory/long_term_memory.sqlite3`

## 安装与启动

### 1.拉取源码到本地

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 启动后端

```powershell
uvicorn backend.src.main:app --reload
```

默认地址：

- `http://127.0.0.1:8000`
- 接口文档：`http://127.0.0.1:8000/docs`

### 4. 启动前端

```powershell
python -m http.server 5500 -d frontend
```

访问地址：

- `http://127.0.0.1:5500`

## 接口说明

### 流式聊天接口

- `POST /api/v1/chat/stream`
- `Content-Type: application/json`
- 返回类型：`text/event-stream`

请求体示例：

```json
{
  "query": "我当前环境下应该怎么保养机器人？",
  "session_id": "demo-session-id",
  "user_id": "demo-user-id"
}
```

字段说明：

- `query`：当前用户问题
- `session_id`：用于绑定同一段短期会话上下文
- `user_id`：用于绑定同一用户的长期记忆

### SSE 返回事件

后端当前会返回三类事件：

- `snapshot`：前端展示“正在思考中...”
- `delta`：最终答案的增量字符流
- `final`：最终完整答案

说明：

- 当前实现没有单独提供 `GET /api/v1/health`
- 文档页 `/docs` 可用于直接查看已注册接口

## 会话与记忆机制

### 短期记忆

- 由 LangGraph 的 `InMemorySaver` 管理
- 使用 `session_id` 作为 `thread_id`
- 同一个 `session_id` 下，多轮对话会自动续接上下文
- 服务重启后，短期记忆会丢失

### 长期记忆

- 使用 `user_id` 作为用户标识
- 持久化存储在 SQLite 中
- 进入 Agent 前会先注入和当前问题相关的长期记忆
- 当前采用规则抽取，优先沉淀用户画像与稳定偏好

目前已覆盖的长期记忆信息包括：

- 称呼
- 所在城市
- 设备型号
- 户型
- 是否有宠物
- 预算范围
- 偏好信息
- 历史问题背景

## 前端行为

当前前端页面的交互逻辑如下：

- 首次进入页面时自动生成并缓存 `session_id`
- 首次进入页面时自动生成并缓存 `user_id`
- 点击“清空会话”只会重置 `session_id`
- 清空会话不会删除 `user_id`，因此长期记忆仍然保留
- 前端不再自己维护完整历史消息，历史上下文由后端托管

## 依赖栈

主要依赖如下：

- `fastapi`
- `uvicorn`
- `pydantic`
- `langchain`
- `langgraph`
- `langchain-chroma`
- `chromadb`
- `dashscope`
- `pypdf`

## 当前状态与后续方向

当前项目重点已经从“单页 Demo”演进为“可持续扩展的智能客服雏形”，现阶段已经打通：

- 前后端分离
- 知识库检索
- Agent 工具编排
- 流式输出
- 长期记忆闭环

后续可以继续补强的方向包括：

- 健康检查与运维接口
- 知识库管理后台
- 会话管理与会话持久化
- 更完善的前端体验
- 更智能的长期记忆抽取与召回策略
