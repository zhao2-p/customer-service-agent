import hashlib
import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from backend.src.core.logger import logger


def get_file_md5_hex(filepath: str) -> str | None:
    # 通过 MD5 判断文件是否已经入库，用来避免重复建立向量。
    if not os.path.exists(filepath):
        logger.error("[md5] file not found: %s", filepath)
        return None

    if not os.path.isfile(filepath):
        logger.error("[md5] path is not a file: %s", filepath)
        return None

    md5_obj = hashlib.md5()     # 创建一个 MD5 对象
    try:
        # 以二进制只读模式打开文件
        with open(filepath, "rb") as file:
            # 分块读取文件（每块 4096 字节），避免大文件占用过多内存
            while chunk := file.read(4096):
                # 逐块更新 MD5 哈希值
                md5_obj.update(chunk)
        # 返回十六进制格式的 MD5 哈希字符串
        return md5_obj.hexdigest()
    except Exception as exc:
        # 记录错误日志并返回 None
        logger.error("[md5] failed for %s: %s", filepath, str(exc))
        return None


def listdir_with_allowed_type(path: str, allowed_types: tuple[str, ...]) -> tuple[str, ...]:
    # 只返回知识库允许的文件类型，例如 txt / pdf。
    if not os.path.isdir(path):
        logger.error("[listdir_with_allowed_type] %s is not a directory", path)
        return tuple()

    files: list[str] = []
    for filename in os.listdir(path):
        if filename.endswith(allowed_types):
            files.append(os.path.join(path, filename))

    return tuple(files)


def pdf_loader(filepath: str, passwd=None) -> list[Document]:
    # LangChain 文档加载器会把文件转成统一的 Document 结构。
    return PyPDFLoader(filepath, passwd).load()


def txt_loader(filepath: str) -> list[Document]:
    return TextLoader(filepath, encoding="utf-8").load()    # LangChain 文档加载器会把文件转成统一的 Document 结构。
