import os

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from backend.app.core.config import chroma_conf
from backend.app.core.logger import logger
from backend.app.core.paths import get_abs_path
from backend.app.infra.llm.factory import chat_model
from backend.app.infra.vectorstore.chroma_store import VectorStoreService
from backend.app.agents.services.prompt_service import load_rag_prompts


class RagSummarizeService:
    def __init__(self):
        self.vector_store = VectorStoreService()
        # 服务初始化时按需检查知识库，确保首次启动也能直接检索。
        self._ensure_vector_store_ready()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _ensure_vector_store_ready(self):
        md5_file_path = get_abs_path(chroma_conf["md5_hex_store"])
        persist_directory = get_abs_path(chroma_conf["persist_directory"])

        # `md5.text` 和持久化目录同时存在时，认为知识库已经完成初始化。
        if os.path.exists(md5_file_path) and os.path.isdir(persist_directory):
            return

        logger.info("[RAG] vector store is not initialized, start loading documents")
        self.vector_store.load_document()

    def _init_chain(self):
        return self.prompt_template | self.model | StrOutputParser()

    def retriever_docs(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    def rag_summarize(self, query: str) -> str:
        context_docs = self.retriever_docs(query)

        # 将检索到的文档手动拼成上下文，再交给总结提示词模板。
        context = ""
        for index, doc in enumerate(context_docs, start=1):
            context += f"【参考资料{index}】 参考资料：{doc.page_content} | 参考元数据：{doc.metadata}\n"

        return self.chain.invoke({"input": query, "context": context})


if __name__ == "__main__":
    rag_service = RagSummarizeService()
    print(rag_service.rag_summarize("小户型适合哪些扫地机器人？"))
