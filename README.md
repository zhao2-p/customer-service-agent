# Customer Service Agent

一个面向扫地机器人/扫拖一体机场景的智能客服项目，采用前后端分离架构，核心能力基于 `Agent + RAG + LLM + 长期记忆`。

项目当前提供：

- 基于知识库的问答
- Agent 工具调用与多步推理
- Chroma 向量检索
- 基于 `session_id` 的短期会话记忆
- 基于 `user_id` 的长期记忆注入与持久化
- 通过 SSE 向前端流式返回最终回复

## Features

- `FastAPI` 提供后端 API
- `HTML + CSS + JavaScript` 提供轻量前端页面
- `LangChain + LangGraph` 驱动 Agent 编排
- `DashScope / Tongyi` 提供聊天模型与向量模型
- `Chroma` 存储知识库向量索引
- `SQLite` 持久化长期记忆

## Project Structure

```text
customer_service_agent/
├─ backend/
│  ├─ src/                     # 后端源码
│  │  ├─ agent/               # Agent 能力包，对外暴露 ChatAgentService
│  │  ├─ api/                 # FastAPI 路由与请求模型
│  │  ├─ core/                # 配置、日志、路径
│  │  ├─ infra/               # LLM、向量库、文件、存储基础设施
│  │  └─ main.py              # FastAPI 入口
│  ├─ data/
│  │  ├─ knowledge/           # 知识库原始数据
│  │  └─ external/            # 外部数据源
│  ├─ database/
│  │  ├─ chroma/              # Chroma 持久化目录
│  │  └─ memory/              # SQLite 长期记忆数据库
│  └─ logs/                   # 运行日志
├─ config/                    # YAML 配置
├─ frontend/                  # 前端页面
├─ requirements.txt
└─ README.md
```

## Architecture

一次聊天请求的大致链路如下：

1. 前端提交 `query`、`session_id`、`user_id`
2. 后端根据 `user_id` 读取长期记忆，构造 `memory_context`
3. Agent 根据需要调用 RAG、天气、外部数据等工具
4. 大模型生成最终回复
5. 后端通过 SSE 将回复按字符流式返回给前端
6. 回答结束后，从本轮输入中提取可沉淀的长期记忆并写入 SQLite

## Tech Stack

- `FastAPI`
- `Uvicorn`
- `Pydantic`
- `LangChain`
- `LangGraph`
- `ChromaDB`
- `DashScope`
- `SQLite`

## Requirements

- Python `3.11+` 推荐
- 可访问 DashScope 服务
- 已安装 `pip`

## Installation

### 1. Clone the repository

```powershell
git clone <your-repo-url>
cd customer_service_agent
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

本项目的大模型 API Key 不写在仓库中，而是从本地环境变量读取。

当前项目使用的是 DashScope 生态下的模型与向量服务，因此你需要配置：

```powershell
$env:DASHSCOPE_API_KEY="your_api_key"
```

如果你希望在当前用户下长期生效，可以在 PowerShell 中执行：

```powershell
[System.Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "your_api_key", "User")
```

配置完成后，重新打开一个终端，再执行下面的命令检查是否生效：

```powershell
echo $env:DASHSCOPE_API_KEY
```

如果你使用的是 `cmd`，可以这样设置：

```cmd
set DASHSCOPE_API_KEY=your_api_key
```

## Configuration

主要配置文件如下：

- `config/rag.yml`：聊天模型、Embedding 模型
- `config/chroma.yml`：Chroma 持久化路径、知识库路径、切片参数
- `config/agent.yml`：外部数据源路径
- `config/prompts.yml`：Prompt 文件路径
- `config/memory.yml`：长期记忆 SQLite 路径、注入数量、抽取开关

当前默认配置：

- 聊天模型：`qwen-plus`
- 向量模型：`text-embedding-v4`
- 知识库目录：`backend/data/knowledge`
- 长期记忆库：`backend/database/memory/long_term_memory.sqlite3`

## Run

### Start backend

```powershell
uvicorn backend.src.main:app --reload
```

默认地址：

- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

### Start frontend

```powershell
python -m http.server 5500 -d frontend
```

访问地址：

- `http://127.0.0.1:5500`

## API

### Streaming chat

- `POST /api/v1/chat/stream`
- `Content-Type: application/json`
- Response: `text/event-stream`

请求示例：

```json
{
  "query": "我当前环境下应该怎么保养机器人？",
  "session_id": "demo-session-id",
  "user_id": "demo-user-id"
}
```

字段说明：

- `query`：当前用户问题
- `session_id`：同一会话的短期上下文标识
- `user_id`：同一用户的长期记忆标识

SSE 事件类型：

- `snapshot`：前端显示“正在思考中...”
- `delta`：最终回复的增量字符流
- `final`：最终完整回复

## Memory Design

### Short-term memory

- 使用 `LangGraph InMemorySaver`
- 以 `session_id` 作为 `thread_id`
- 同一 `session_id` 下可自动续接上下文
- 服务重启后短期记忆会丢失

### Long-term memory

- 以 `user_id` 作为用户标识
- 持久化到 SQLite
- 进入 Agent 前先注入相关长期记忆
- 回答结束后根据规则抽取用户画像和偏好信息

当前长期记忆覆盖的信息包括：

- 用户称呼
- 所在城市
- 设备型号
- 户型
- 是否有宠物
- 预算范围
- 偏好信息
- 历史问题背景

## Data Layout

### Knowledge data

存放位置：`backend/data/knowledge`

包含知识库原始文本、PDF 等内容，用于构建向量索引。

### External data

存放位置：`backend/data/external`

用于模拟外部系统数据源，例如 `records.csv`。

## Development Notes

- 当前项目从 `backend.src.agent.chat_agent_service.ChatAgentService` 统一调用 Agent
- `backend/src/agent` 是核心能力包
- `backend/src/infra` 放底层实现，不直接承载业务编排

## Known Limitations

- 当前对外主要提供流式聊天接口
- 没有单独的健康检查接口
- 短期记忆为内存级，不跨服务重启保留
- 模型调用依赖本地环境变量和外部网络连通性



