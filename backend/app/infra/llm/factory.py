from abc import ABC, abstractmethod
from typing import Optional

from langchain_community.chat_models.tongyi import BaseChatModel, ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings

from backend.app.core.config import rag_conf


class BaseModelFactory(ABC):
    # 工厂基类：约束不同类型模型都提供统一的 `generator` 接口。
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        raise NotImplementedError


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        # 聊天模型供 Agent 和 RAG 总结链使用。
        return ChatTongyi(model=rag_conf["chat_model_name"])


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        # 向量模型负责把文本转成 embedding，供 Chroma 检索使用。
        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])


# 这里直接生成全局单例，方便各模块按需复用。
chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
