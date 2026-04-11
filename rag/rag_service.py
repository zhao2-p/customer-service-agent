"""
总结服务类：用户提问，搜索参考资料，将提问和参考资料提交给模型，让模型总结回复
"""
import os

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from model.factory import chat_model
from rag.vector_store import VectorStoreService
from utils.config_handler import chroma_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
from utils.prompt_loader import load_rag_prompts


def print_prompt(prompt):
    print("=" * 20)
    print(prompt.to_string())
    print("=" * 20)
    return prompt


class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self._ensure_vector_store_ready()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _ensure_vector_store_ready(self):
        md5_file_path = get_abs_path(chroma_conf["md5_hex_store"])
        persist_directory = get_abs_path(chroma_conf["persist_directory"])

        if os.path.exists(md5_file_path) and os.path.isdir(persist_directory):
            return

        logger.info("[RAG] 检测到知识库未初始化，开始加载文档并构建向量库")
        self.vector_store.load_document()

    def _init_chain(self):
        chain = self.prompt_template | self.model | StrOutputParser()
        return chain

    def retriever_docs(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    def rag_summarize(self, query: str) -> str:
        context_docs = self.retriever_docs(query)

        context = ""
        counter = 0
        for doc in context_docs:
            counter += 1
            context += f"【参考资料{counter}】 参考资料：{doc.page_content} | 参考元数据：{doc.metadata}\n"

        return self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )


if __name__ == '__main__':
    rag = RagSummarizeService()

    print(rag.rag_summarize("小户型适合哪些扫地机器人"))
