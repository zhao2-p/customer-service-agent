# 智能客服系统

这是一个面向扫地机器人与扫拖一体机器人场景的智能客服系统项目。

当前阶段，系统的核心功能是智能客服问答：

- 用户输入问题
- Agent 根据问题自主决定是否调用工具
- RAG 从知识库中检索专业资料
- 大模型整合检索结果并生成最终答复

项目已经完成从单体 Demo 向前后端分离雏形的重构：

- 后端使用 `FastAPI`
- 前端使用纯 `HTML + CSS + JavaScript`
- 问答能力基于 `Agent + RAG + LLM`

## 当前目标

当前项目的主要目标是先把“智能客服问答”这一条链路做稳定、做完整，包括：

- 智能问答体验
- 知识库检索能力
- 前后端接口联调
- 最终答复的可用性与专业性

后续会在此基础上逐步扩展为更完整的智能客服系统，例如：

- 知识库管理
- 会话管理
- 用户管理
- 报告生成
- 后台管理能力

## 项目结构

```text
AI大模型RAG与智能体开发_Agent项目/
├─ backend/
│  ├─ app/
│  │  ├─ api/          # FastAPI 接口层
│  │  ├─ agents/       # Agent 编排、工具、中间件
│  │  ├─ services/     # RAG、Prompt 等业务服务
│  │  ├─ infra/        # 模型、向量库、文件加载等基础设施
│  │  ├─ core/         # 配置、路径、日志
│  │  └─ main.py       # FastAPI 启动入口
│  ├─ data/            # 知识库原始数据、外部数据
│  ├─ chroma_db/       # Chroma 持久化向量库
│  └─ logs/            # 运行日志
├─ frontend/           # 简单前端会话页面
├─ config/             # YAML 配置文件
├─ prompts/            # Prompt 模板
├─ requirements.txt    # Python 依赖
└─ README.md
```

## 当前能力

当前已经具备的能力：

- 基于知识库的智能客服问答
- Agent 工具调用
- 知识库自动初始化与向量检索
- FastAPI 后端接口
- 简单前端聊天页面
- 前后端分离调用

当前聊天页面的显示策略是：

- 请求发起后先显示“正在思考...”
- 中间思考过程不展示给用户
- 最终只展示最后答复

## 启动方式

### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

### 2. 启动后端

```powershell
uvicorn backend.app.main:app --reload
```

后端启动后可访问：

- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- 接口文档：`http://127.0.0.1:8000/docs`

### 3. 启动前端页面

```powershell
python -m http.server 5500 -d frontend
```

前端访问地址：

- `http://127.0.0.1:5500`

## 当前核心接口

### 健康检查

- `GET /api/v1/health`

### 智能客服问答

- `POST /api/v1/chat/stream`

请求体示例：

```json
{
  "query": "我现在的环境下应该怎么保养机器人？",
  "history": [
    {
      "role": "user",
      "content": "你好"
    },
    {
      "role": "assistant",
      "content": "你好，请问有什么可以帮您？"
    }
  ]
}
```

## 技术方向

当前技术方向已经明确：

- 后端：`FastAPI`
- 前端：先用简单静态页面验证，再逐步升级
- 核心能力：`Agent + RAG + LLM`
- 系统定位：智能客服系统

## 后续规划

下一阶段建议优先补充这些模块：

1. 知识库管理
2. 会话管理
3. 报告生成
4. 更完整的前端页面

## 说明

这个项目当前不是“纯聊天页面项目”，而是“以智能客服问答为核心能力的系统雏形”。

当前重点不是页面复杂度，而是先把问答链路、知识库链路、接口链路打稳。
