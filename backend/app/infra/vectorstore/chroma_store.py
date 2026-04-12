import os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.core.config import chroma_conf
from backend.app.core.logger import logger
from backend.app.core.paths import get_abs_path
from backend.app.infra.files.file_loader import (
    get_file_md5_hex,
    listdir_with_allowed_type,
    pdf_loader,
    txt_loader,
)
from backend.app.infra.llm.factory import embed_model


class VectorStoreService:       #向量存储服务
    def __init__(self):
        # Chroma 的持久化目录和去重文件路径都来自配置。
        persist_directory = get_abs_path(chroma_conf["persist_directory"])      # 向量库目录
        self.md5_file_path = get_abs_path(chroma_conf["md5_hex_store"])     # md5 缓存文件路径

        # Chroma 是当前项目的向量数据库。
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=persist_directory,
        )

        # 大文档先切块，再写入向量库；否则检索粒度会太粗。
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        # Retriever 是对向量库的高层封装，LangChain 下游通常直接消费它。
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def load_document(self):
        # 用 md5 记录已经入库的文件，避免重复切片和重复写入向量库。
        def check_md5_hex(md5_for_check: str | None):
            # 如果md5 为空，则不进行去重
            if not md5_for_check:
                return False

            # 如果 md5 文件不存在，则创建一个空文件
            if not os.path.exists(self.md5_file_path):
                open(self.md5_file_path, "w", encoding="utf-8").close()
                return False

            # 检查 md5 是否已经存在
            with open(self.md5_file_path, "r", encoding="utf-8") as file:
                for line in file.readlines():
                    # 如果找到，则返回 True
                    if line.strip() == md5_for_check:
                        return True
            return False

        def save_md5_hex(md5_for_check: str | None):
            if not md5_for_check:
                return

            with open(self.md5_file_path, "a", encoding="utf-8") as file:
                file.write(md5_for_check + "\n")

        def get_file_documents(read_path: str) -> list[Document]:
            # 根据文件后缀名，选择对应的加载器，加载器会把文件转成 Document 列表。
            if read_path.endswith("txt"):
                return txt_loader(read_path)
            if read_path.endswith("pdf"):
                return pdf_loader(read_path)
            return []

        allowed_files_path = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"])
        )

        for path in allowed_files_path:
            md5_hex = get_file_md5_hex(path)      # 获取文件的 md5

            if check_md5_hex(md5_hex):      # 检查文件是否已经入库，如果为True则表示已经入库，则跳过本次循环
                logger.info("[load_document] file already indexed: %s", path)
                continue

            try:
                documents = get_file_documents(path)    # 将路径path下的文件转换为 Document 结构
                if not documents:
                    logger.warning("[load_document] empty documents: %s", path)
                    continue

                # 大文档先切块，再写入向量库
                split_document = self.spliter.split_documents(documents)
                if not split_document:
                    logger.warning("[load_document] empty chunks after split: %s", path)
                    continue

                # Chroma 会自动持久化到 `persist_directory`，这里不需要手动保存。
                self.vector_store.add_documents(split_document)
                save_md5_hex(md5_hex)
                logger.info("[load_document] indexed: %s", path)
            except Exception as exc:
                logger.error("[load_document] failed for %s: %s", path, str(exc), exc_info=True)
                continue


if __name__ == "__main__":
    vector_store = VectorStoreService()
    vector_store.load_document()

    retriever = vector_store.get_retriever()
    result = retriever.invoke("小户型适合哪些扫地机器人？")
    for item in result:
        print(item.page_content)
        print("-" * 20)
