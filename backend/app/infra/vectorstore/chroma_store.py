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


class VectorStoreService:
    def __init__(self):
        # 向量库和 md5 记录都统一落在项目根目录，避免从不同工作目录启动时重复生成。
        persist_directory = get_abs_path(chroma_conf["persist_directory"])
        self.md5_file_path = get_abs_path(chroma_conf["md5_hex_store"])

        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=persist_directory,
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def load_document(self):
        # 使用 md5 记录已入库文件，避免重复切片和重复写入向量库。
        def check_md5_hex(md5_for_check: str | None):
            if not md5_for_check:
                return False

            if not os.path.exists(self.md5_file_path):
                open(self.md5_file_path, "w", encoding="utf-8").close()
                return False

            with open(self.md5_file_path, "r", encoding="utf-8") as file:
                for line in file.readlines():
                    if line.strip() == md5_for_check:
                        return True
            return False

        def save_md5_hex(md5_for_check: str | None):
            if not md5_for_check:
                return

            with open(self.md5_file_path, "a", encoding="utf-8") as file:
                file.write(md5_for_check + "\n")

        def get_file_documents(read_path: str) -> list[Document]:
            if read_path.endswith("txt"):
                return txt_loader(read_path)
            if read_path.endswith("pdf"):
                return pdf_loader(read_path)
            return []

        allowed_files_path = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            md5_hex = get_file_md5_hex(path)

            if check_md5_hex(md5_hex):
                logger.info("[load_document] file already indexed: %s", path)
                continue

            try:
                documents = get_file_documents(path)
                if not documents:
                    logger.warning("[load_document] empty documents: %s", path)
                    continue

                split_document = self.spliter.split_documents(documents)
                if not split_document:
                    logger.warning("[load_document] empty chunks after split: %s", path)
                    continue

                # Chroma 会自动持久化到 `persist_directory`，这里不需要额外手动保存。
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
